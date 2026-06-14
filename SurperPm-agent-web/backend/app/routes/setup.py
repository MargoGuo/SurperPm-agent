"""Setup wizard routes — team profile + personal profile (local file-based)."""
import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException

from app.config import settings
from app.services import github_client
from app.services import session as session_svc
from app.services.knowledge_store import get_store

_logger = logging.getLogger(__name__)

router = APIRouter()

SESSION_COOKIE = "SuperPmAgent_session"
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


def _profiles_dir() -> Path:
    """Return the local profiles directory inside the knowledge repo."""
    knowledge_path = Path(settings.knowledge_repo_path) if settings.knowledge_repo_path else None
    if not knowledge_path or not knowledge_path.is_dir():
        store = get_store()
        knowledge_path = store._root.parent
    return knowledge_path / "profiles" / "users"


def _profile_path(username: str) -> Path:
    d = _profiles_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{username}.md"


@router.get("/ping")
async def ping() -> dict:
    return {"ok": True}


@router.get("/init-state")
async def init_state(
    SuperPmAgent_session: Annotated[str | None, Cookie()] = None,
) -> dict:
    """Whether the system is initialized + whether the caller is the founder."""
    from app.database import async_session
    from app.models.global_config import GlobalConfig

    username = ""
    if SuperPmAgent_session:
        data = session_svc.decode(SuperPmAgent_session)
        if data:
            username = data.get("username", "")

    store = get_store()
    store_settings = store.get_settings()
    initialized = bool(store_settings.get("knowledge_repo_url"))

    async with async_session() as session:
        cfg = await session.get(GlobalConfig, 1)
        founder = cfg.founder_username if cfg else None

    return {
        "initialized": initialized,
        "is_founder": bool(founder) and username == founder,
    }


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
    team_md = team_md_res if isinstance(team_md_res, str) else ""
    team_md_exists = bool(team_md)

    total = sum(int(v) for v in languages.values()) if languages else 0
    total = total or 1
    lang_pct = {lang: round(int(v) / total * 100) for lang, v in languages.items()}

    return {
        "team_name": repo_name,
        "description": description,
        "members": members[:10],
        "languages": lang_pct,
        "team_md_exists": team_md_exists,
        "team_md": team_md,
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
    answers: dict | None = None
    auto_detected_languages: dict = {}

    if username:
        profile_file = _profile_path(username)
        if profile_file.is_file():
            md = profile_file.read_text("utf-8")
            completed = True
            answers = _parse_profile_json(md)

    if token and repo:
        owner, repo_name = _split_repo(repo)
        loop = asyncio.get_event_loop()

        async def _safe(fn, *args):
            try:
                return await loop.run_in_executor(None, fn, *args)
            except Exception:
                return None

        languages_res = await _safe(
            github_client.get_repo_languages, token, owner, repo_name
        )
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
    username = sess.get("username", "")
    if not username:
        raise HTTPException(status_code=400, detail="username not in session")

    answers = payload.get("answers", {})
    auto_lang = payload.get("auto_detected_languages", {})
    md = _render_profile_md(username, answers, auto_lang)

    profile_file = _profile_path(username)
    profile_file.write_text(md, encoding="utf-8")
    return {"ok": True}


@router.post("/update-profile")
async def update_profile(
    payload: dict,
    SuperPmAgent_session: Annotated[str | None, Cookie()] = None,
) -> dict:
    sess = _get_session(SuperPmAgent_session)
    username = sess.get("username", "")
    if not username:
        raise HTTPException(status_code=400, detail="username not in session")

    answers = payload.get("answers", {})
    md = _render_profile_md(username, answers, {})

    profile_file = _profile_path(username)
    profile_file.write_text(md, encoding="utf-8")
    return {"ok": True}


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
    return json.dumps(answers, ensure_ascii=False, default=str)


def _parse_profile_json(md: str) -> dict | None:
    m = re.search(r'<!-- PROFILE_JSON\n(.*?)\n-->', md, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _label(cat: str, answers: dict, key: str) -> str:
    return _LABELS[cat].get(answers.get(key, ""), answers.get(key, ""))


def _render_profile_md(username: str, answers: dict, auto_lang: dict) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d")
    role = _label("role", answers, "role")
    exp = _label("experience", answers, "experience")
    review = _label("review_style", answers, "review_style")
    decision = _label("decision_style", answers, "decision_style")
    test = _label("test_approach", answers, "test_approach")
    comm = _label("communication", answers, "communication")
    tech_stack = answers.get("tech_stack", [])
    if isinstance(tech_stack, list):
        tech_stack = ", ".join(tech_stack)
    lang_items = [f"- {lang}: {pct}%" for lang, pct in auto_lang.items()]
    lang_lines = "\n".join(lang_items) if auto_lang else "- (none)"

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
