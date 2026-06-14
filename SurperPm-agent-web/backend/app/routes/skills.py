"""Skills API — filesystem-based, reads from knowledge/skills/."""

import logging
import re
from pathlib import Path

import requests as http_requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routes.deps import require_auth

router = APIRouter()
_logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _skills_root() -> Path:
    from app.services.knowledge_store import get_store

    store = get_store()
    root = store._root.parent / "skills"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _parse_frontmatter(text: str) -> dict:
    fm: dict = {}
    fm_match = _FRONTMATTER_RE.match(text)
    if not fm_match:
        return fm
    for line in fm_match.group(1).split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip("\"'")
    return fm


def _parse_skill_md(path: Path) -> dict | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    body = _FRONTMATTER_RE.sub("", text, count=1).strip()
    return {
        "name": fm.get("name", path.parent.name),
        "description": fm.get("description", ""),
        "version": fm.get("version", ""),
        "tags": fm.get("tags", ""),
        "body": body,
    }


def _scan_skills() -> list[dict]:
    root = _skills_root()
    results = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        skill_md = d / "SKILL.md"
        parsed = _parse_skill_md(skill_md)
        if parsed:
            parsed["slug"] = d.name
            results.append(parsed)
    return results


class SkillCreate(BaseModel):
    name: str
    description: str | None = None
    content: str


class SkillImportUrl(BaseModel):
    url: str


class SkillValidateRequest(BaseModel):
    content: str


class ValidationIssue(BaseModel):
    severity: str
    field: str
    message: str


class SkillValidateResponse(BaseModel):
    valid: bool
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []


@router.get("")
async def list_skills(
    workspace_id: str,
    _user: dict = Depends(require_auth),
):
    return _scan_skills()


@router.get("/{slug}")
async def get_skill(
    workspace_id: str,
    slug: str,
    _user: dict = Depends(require_auth),
):
    root = _skills_root()
    skill_dir = root / slug
    parsed = _parse_skill_md(skill_dir / "SKILL.md")
    if not parsed:
        raise HTTPException(status_code=404, detail="Skill not found")
    parsed["slug"] = slug
    files = []
    for f in sorted(skill_dir.rglob("*")):
        if f.is_file() and not f.name.startswith("."):
            files.append({
                "path": str(f.relative_to(skill_dir)),
                "content": f.read_text(
                    encoding="utf-8", errors="replace",
                ),
            })
    parsed["files"] = files
    return parsed


@router.post("", status_code=201)
async def create_skill(
    workspace_id: str,
    body: SkillCreate,
    _user: dict = Depends(require_auth),
):
    root = _skills_root()
    slug = (
        re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-")
        or "skill"
    )
    skill_dir = root / slug
    if skill_dir.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Skill '{slug}' already exists",
        )
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(body.content, encoding="utf-8")
    parsed = _parse_skill_md(skill_dir / "SKILL.md")
    parsed["slug"] = slug
    return parsed


@router.delete("/{slug}", status_code=204)
async def delete_skill(
    workspace_id: str,
    slug: str,
    _user: dict = Depends(require_auth),
):
    import shutil

    root = _skills_root()
    skill_dir = root / slug
    if not skill_dir.is_dir():
        raise HTTPException(status_code=404, detail="Skill not found")
    shutil.rmtree(skill_dir)


@router.post("/import", status_code=201)
async def import_skill_from_url(
    workspace_id: str,
    body: SkillImportUrl,
    _user: dict = Depends(require_auth),
):
    url = body.url.strip().rstrip("/")
    match = re.match(
        r"https?://github\.com/([^/]+)/([^/]+?)"
        r"(?:/(?:tree|blob)/[^/]+/(.*))?$",
        url,
    )
    if not match:
        raise HTTPException(
            status_code=400, detail=f"Invalid GitHub URL: {url}",
        )

    owner = match.group(1)
    repo = match.group(2)
    subpath = match.group(3) or ""
    token = _user.get("github_token", "")
    if not token:
        raise HTTPException(
            status_code=400, detail="No GitHub token.",
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    api_url = (
        f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{subpath}"
        .rstrip("/")
    )
    resp = http_requests.get(api_url, headers=headers, timeout=15)
    if resp.status_code == 404:
        raise HTTPException(
            status_code=404, detail="GitHub path not found",
        )
    resp.raise_for_status()

    contents = resp.json()
    if not isinstance(contents, list):
        contents = [contents]

    files: list[dict] = []
    _recurse_github_dir(
        headers, owner, repo, contents, subpath, files,
    )
    if not files:
        raise HTTPException(
            status_code=400, detail="No files found at URL",
        )

    skill_name = subpath.split("/")[-1] if subpath else repo
    slug = (
        re.sub(r"[^a-z0-9]+", "-", skill_name.lower()).strip("-")
        or "skill"
    )
    root = _skills_root()
    skill_dir = root / slug
    skill_dir.mkdir(parents=True, exist_ok=True)

    for f_info in files:
        out = skill_dir / f_info["path"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(f_info["content"], encoding="utf-8")

    parsed = _parse_skill_md(skill_dir / "SKILL.md") or {
        "name": skill_name,
        "description": f"Imported from {url}",
    }
    parsed["slug"] = slug
    parsed["source_url"] = url
    return parsed


_BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".zip", ".gz", ".tar", ".bz2", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".pyc", ".pyo", ".class",
}


def _recurse_github_dir(
    headers, owner, repo, contents, base_path, collected,
    max_files=128, depth=0,
):
    if depth > 5 or len(collected) >= max_files:
        return
    for item in contents:
        if len(collected) >= max_files:
            return
        if item["type"] == "dir":
            sub = http_requests.get(
                item["url"], headers=headers, timeout=15,
            )
            if sub.status_code == 200:
                _recurse_github_dir(
                    headers, owner, repo, sub.json(),
                    item["path"], collected, max_files, depth + 1,
                )
        elif item["type"] == "file":
            ext = Path(item["name"]).suffix.lower()
            if ext in _BINARY_EXTS:
                continue
            rel = item["path"]
            if base_path and rel.startswith(base_path):
                rel = rel[len(base_path):].lstrip("/")
            dl = http_requests.get(
                item.get("download_url", ""),
                headers=headers, timeout=15,
            )
            if dl.status_code == 200:
                collected.append({"path": rel, "content": dl.text})


@router.post("/validate")
async def validate_skill(
    workspace_id: str,
    body: SkillValidateRequest,
    _user: dict = Depends(require_auth),
) -> SkillValidateResponse:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    content = body.content

    fm = _parse_frontmatter(content)
    if not fm:
        warnings.append(ValidationIssue(
            severity="warning", field="frontmatter",
            message="No YAML frontmatter found.",
        ))

    if not fm.get("name"):
        errors.append(ValidationIssue(
            severity="error", field="frontmatter.name",
            message="Missing required field: name",
        ))
    if not fm.get("description"):
        errors.append(ValidationIssue(
            severity="error", field="frontmatter.description",
            message="Missing required field: description",
        ))

    body_text = _FRONTMATTER_RE.sub("", content, count=1).strip()
    if not body_text:
        errors.append(ValidationIssue(
            severity="error", field="structure.body",
            message="SKILL.md body is empty after frontmatter",
        ))
    elif "## " not in body_text:
        errors.append(ValidationIssue(
            severity="error", field="structure.sections",
            message="Must contain at least one ## section header",
        ))

    return SkillValidateResponse(
        valid=len(errors) == 0, errors=errors, warnings=warnings,
    )
