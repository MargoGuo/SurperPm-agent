"""Setup wizard routes — team profile + personal profile."""
import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException

from app.services import github_client
from app.services import session as session_svc

_logger = logging.getLogger(__name__)

router = APIRouter()

SESSION_COOKIE = "SuperPmAgent_session"
PROFILE_PATH = "knowledge/profiles/{username}.md"
TEAM_PROFILE_PATH = "knowledge/profiles/team.md"


def _get_session(cookie: str | None) -> dict:
    if not cookie:
        raise HTTPException(status_code=401, detail="not_logged_in")
    data = session_svc.decode(cookie)
    if not data:
        raise HTTPException(status_code=401, detail="invalid_session")
    return data


def _split_repo(repo: str) -> tuple[str, str]:
    parts = repo.split("/")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="repo must be owner/repo")
    return parts[0], parts[1]


@router.get("/ping")
async def ping() -> dict:
    return {"ok": True}


# ── Team profile ──────────────────────────────────────────────


@router.get("/team-profile")
async def team_profile(
    SuperPmAgent_session: Annotated[str | None, Cookie()] = None,
) -> dict:
    sess = _get_session(SuperPmAgent_session)
    token = sess.get("github_token", "")
    repo = sess.get("repo", "")
    if not token or not repo:
        raise HTTPException(status_code=400, detail="repo not configured")

    owner, repo_name = _split_repo(repo)

    # Run all 4 GitHub API calls in parallel via thread pool
    loop = asyncio.get_event_loop()

    async def _safe(fn, *args):
        try:
            return await loop.run_in_executor(None, fn, *args)
        except Exception:
            _logger.warning("%s failed for %s", fn.__name__, repo, exc_info=True)
            return None

    languages_res, members_res, info_res, team_md_res = await asyncio.gather(
        _safe(github_client.get_repo_languages, token, owner, repo_name),
        _safe(github_client.get_repo_collaborators, token, owner, repo_name),
        _safe(github_client.get_repo_info, token, owner, repo_name),
        _safe(github_client.read_file_from_repo, token, owner, repo_name, TEAM_PROFILE_PATH),
    )

    languages = languages_res if isinstance(languages_res, dict) else {}
    members = members_res if isinstance(members_res, list) else []
    info = info_res if isinstance(info_res, dict) else {}
    description = info.get("description", "")
    team_md_exists = team_md_res is not None

    total = sum(int(v) for v in languages.values()) if languages else 0
    total = total or 1
    lang_pct = {lang: round(int(v) / total * 100) for lang, v in languages.items()}

    return {
        "team_name": repo_name,
        "description": description,
        "members": members[:10],
        "languages": lang_pct,
        "team_md_exists": team_md_exists,
    }


# ── Setup state ───────────────────────────────────────────────


@router.get("/state")
async def state(
    SuperPmAgent_session: Annotated[str | None, Cookie()] = None,
) -> dict:
    sess = _get_session(SuperPmAgent_session)
    token = sess.get("github_token", "")
    repo = sess.get("repo", "")
    username = sess.get("username", "")

    completed = False
    auto_detected_languages: dict = {}

    if token and repo and username:
        owner, repo_name = _split_repo(repo)
        loop = asyncio.get_event_loop()
        profile_path = PROFILE_PATH.format(username=username)

        async def _safe(fn, *args):
            try:
                return await loop.run_in_executor(None, fn, *args)
            except Exception:
                return None

        existing_res, languages_res = await asyncio.gather(
            _safe(github_client.read_file_from_repo, token, owner, repo_name, profile_path),
            _safe(github_client.get_repo_languages, token, owner, repo_name),
        )

        completed = existing_res is not None
        answers = _parse_profile_json(existing_res) if completed else None

        languages = languages_res if isinstance(languages_res, dict) else {}
        if languages:
            total = sum(int(v) for v in languages.values()) or 1
            auto_detected_languages = {
                lang: round(int(v) / total * 100) for lang, v in languages.items()
            }

    return {
        "completed": completed,
        "auto_detected_languages": auto_detected_languages,
        "answers": answers,
    }


# ── Finish (save profile) ─────────────────────────────────────


@router.post("/finish")
async def finish(
    payload: dict,
    SuperPmAgent_session: Annotated[str | None, Cookie()] = None,
) -> dict:
    sess = _get_session(SuperPmAgent_session)
    token = sess.get("github_token", "")
    repo = sess.get("repo", "")
    username = sess.get("username", "")
    if not token or not repo:
        raise HTTPException(status_code=400, detail="repo not configured")

    answers = payload.get("answers", {})
    auto_lang = payload.get("auto_detected_languages", {})
    owner, repo_name = _split_repo(repo)
    path = PROFILE_PATH.format(username=username)
    md = _render_profile_md(username, answers, auto_lang)

    try:
        result = github_client.commit_file(
            token, owner, repo_name, path, md,
            f"Update personal profile for {username}",
        )
        return {"ok": True, "sha": result["sha"]}
    except Exception as e:
        _logger.error("commit failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save profile")


@router.post("/update-profile")
async def update_profile(
    payload: dict,
    SuperPmAgent_session: Annotated[str | None, Cookie()] = None,
) -> dict:
    sess = _get_session(SuperPmAgent_session)
    token = sess.get("github_token", "")
    repo = sess.get("repo", "")
    username = sess.get("username", "")
    if not token or not repo:
        raise HTTPException(status_code=400, detail="repo not configured")

    answers = payload.get("answers", {})
    owner, repo_name = _split_repo(repo)
    path = PROFILE_PATH.format(username=username)
    md = _render_profile_md(username, answers, {})

    try:
        result = github_client.commit_file(
            token, owner, repo_name, path, md,
            f"Update personal profile for {username}",
        )
        return {"ok": True, "sha": result["sha"]}
    except Exception as e:
        _logger.error("update failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update profile")


# ── Profile MD rendering ──────────────────────────────────────

_LABELS = {
    "role": {"pm": "产品经理", "engineer": "工程师", "lead": "技术负责人",
             "data": "数据工程师", "fullstack": "全栈"},
    "experience": {"junior": "初级 (< 2年)", "mid": "中级 (2-5年)", "senior": "高级 (5年+)"},
    "review_style": {"strict": "严格", "lightweight": "轻量", "fast": "快速合并"},
    "decision_style": {"ask": "先问", "act": "先做", "flexible": "看情况"},
    "test_approach": {"tdd": "先写测试(TDD)", "after": "写完代码再补测试",
                      "critical": "关键逻辑才写测试", "ci": "测试交给CI"},
    "communication": {"concise": "简洁", "standard": "标准", "detailed": "详细"},
}


def _answers_to_json(answers: dict) -> str:
    """将原始 answers 序列化为 JSON，嵌入 markdown 注释中。"""
    return json.dumps(answers, ensure_ascii=False, default=str)


def _parse_profile_json(md: str) -> dict | None:
    """从 markdown 的 PROFILE_JSON 注释中提取原始 answers。"""
    m = re.search(r'<!-- PROFILE_JSON\n(.*?)\n-->', md, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _render_profile_md(username: str, answers: dict, auto_lang: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    role = _LABELS["role"].get(answers.get("role", ""), answers.get("role", ""))
    exp = _LABELS["experience"].get(answers.get("experience", ""), answers.get("experience", ""))
    review = _LABELS["review_style"].get(answers.get("review_style", ""), answers.get("review_style", ""))
    decision = _LABELS["decision_style"].get(answers.get("decision_style", ""), answers.get("decision_style", ""))
    test = _LABELS["test_approach"].get(answers.get("test_approach", ""), answers.get("test_approach", ""))
    comm = _LABELS["communication"].get(answers.get("communication", ""), answers.get("communication", ""))
    tech_stack = answers.get("tech_stack", [])
    if isinstance(tech_stack, list):
        tech_stack = ", ".join(tech_stack)
    lang_lines = "\n".join(f"- {lang}: {pct}%" for lang, pct in auto_lang.items()) if auto_lang else "- (none)"

    return f"""# Personal Profile

> Generated by SuperPmAgent. Edit directly if needed.

## Identity

- GitHub: {username}
- Updated: {now}

## Role & Experience

- Role: {role}
- Experience: {exp}

## Tech Stack

- Languages: {tech_stack}

## Work Style

- Code Review: {review}
- Decision Style: {decision}
- Test Approach: {test}
- Communication: {comm}

## Auto-detected

{lang_lines}

<!-- PROFILE_JSON
{_answers_to_json(answers)}
-->
"""
