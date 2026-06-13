"""Plugin marketplace — GitHub API file-by-file import, same pattern as skills."""

import json
import logging
import re
import shutil
from pathlib import Path

import requests as http_requests
import urllib3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

# Disable SSL warnings for dev environments with corporate proxies
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from app.config import settings
from app.routes.deps import require_auth, require_founder

router = APIRouter()
_logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"
_MARKETPLACE_CACHE = ".marketplace-cache"


# ── Schemas ─────────────────────────────────────────────────────


class ImportRequest(BaseModel):
    url: str


class PluginInfo(BaseModel):
    name: str
    version: str = "0.0.0"
    description: str | None = None
    author: str | None = None
    source_url: str | None = None
    subdir: str | None = None
    commands: list[str] = []
    skills: list[str] = []
    agents: list[str] = []
    enabled: bool = True
    installed: bool = False


class MarketPlaceStatus(BaseModel):
    imported: bool
    repo_url: str | None = None
    plugins: list[PluginInfo] = []


# ── GitHub helper (same pattern as skill import) ────────────────


def _parse_github_url(url: str) -> tuple[str, str, str, str]:
    """Return (owner, repo, branch, subpath) from GitHub URL."""
    url = url.strip().rstrip("/")
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:/(?:tree|blob)/([^/]+)/(.*))?$", url)
    if not m:
        m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)$", url)
    if not m:
        raise HTTPException(status_code=400, detail=f"Invalid GitHub URL: {url}")
    owner = m.group(1)
    repo = m.group(2).removesuffix(".git")
    branch = m.group(3) or "main"
    subpath = m.group(4) or ""
    return owner, repo, branch, subpath


def _github_headers(user: dict) -> dict:
    token = user.get("github_token", "")
    if not token:
        raise HTTPException(status_code=400, detail="No GitHub token found. Please re-login with GitHub.")
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def _recurse_github_dir(
    headers: dict, owner: str, repo: str, contents: list,
    base_path: str, collected: list, max_files: int = 128, depth: int = 0,
) -> None:
    """Fetch files recursively via GitHub Contents API."""
    if depth > 5 or len(collected) >= max_files:
        return
    for entry in contents:
        if len(collected) >= max_files:
            break
        if entry.get("type") == "dir":
            try:
                resp = http_requests.get(entry["url"], headers=headers, timeout=15, verify=False)
                if resp.status_code == 200:
                    _recurse_github_dir(headers, owner, repo, resp.json(), base_path, collected, max_files, depth + 1)
            except Exception:
                _logger.warning("Skipped dir %s due to fetch error", entry.get("path"))
        elif entry.get("type") == "file":
            name = entry.get("name", "")
            if name.endswith((".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".zip", ".gz")):
                continue
            download_url = entry.get("download_url")
            if not download_url:
                continue
            try:
                resp = http_requests.get(download_url, headers=headers, timeout=15, verify=False)
                if resp.status_code == 200:
                    rel_path = entry.get("path", name)
                    if base_path and rel_path.startswith(base_path + "/"):
                        rel_path = rel_path[len(base_path) + 1:]
                    collected.append({"path": rel_path, "content": resp.text})
            except Exception:
                _logger.warning("Failed to download %s", download_url)


# ── Filesystem helpers ──────────────────────────────────────────


def _plugin_root() -> Path:
    root = settings.plugin_repo_path
    if not root:
        raise HTTPException(status_code=400, detail="PLUGIN_REPO_PATH not configured in .env")
    p = Path(root)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _read_plugin_json(plugin_dir: Path) -> dict | None:
    manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        return None
    try:
        return json.loads(manifest.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


async def _scan_installed() -> list[dict]:
    root = _plugin_root()
    plugins: list[dict] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        manifest = _read_plugin_json(d)
        if not manifest:
            continue
        disabled = (d / ".disabled").exists()
        plugins.append({
            "name": d.name,
            "version": manifest.get("version", "0.0.0"),
            "description": manifest.get("description"),
            "author": manifest.get("author"),
            "source_url": manifest.get("source", manifest.get("homepage")),
            "subdir": manifest.get("subdir"),
            "commands": (
                list(manifest.get("commands", {}).keys())
                if isinstance(manifest.get("commands"), dict) else []
            ),
            "skills": (
                [s.get("name", "") for s in manifest.get("skills", [])]
                if isinstance(manifest.get("skills"), list) else []
            ),
            "agents": (
                [a.get("name", "") for a in manifest.get("agents", [])]
                if isinstance(manifest.get("agents"), list) else []
            ),
            "enabled": not disabled,
            "installed": True,
        })
    return plugins


# ── Marketplace cache ───────────────────────────────────────────


def _marketplace_dir() -> Path:
    return _plugin_root() / _MARKETPLACE_CACHE


def _marketplace_meta_file() -> Path:
    return _marketplace_dir() / ".meta.json"


def _read_marketplace_repo_url() -> str | None:
    mf = _marketplace_meta_file()
    if not mf.is_file():
        return None
    try:
        return json.loads(mf.read_text(encoding="utf-8")).get("repo_url")
    except (ValueError, OSError):
        return None


def _save_marketplace_meta(repo_url: str) -> None:
    d = _marketplace_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / ".meta.json").write_text(json.dumps({"repo_url": repo_url}, indent=2), encoding="utf-8")


def _read_marketplace_json() -> list[dict]:
    d = _marketplace_dir()
    mkt = d / "marketplace.json"
    if not mkt.is_file():
        return []
    try:
        data = json.loads(mkt.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    raw = data.get("plugins", []) if isinstance(data, dict) else data if isinstance(data, list) else []
    repo_url = _read_marketplace_repo_url() or ""
    # Normalize: fill source_url from repo if missing, subdir from path if missing
    for p in raw:
        if not p.get("source"):
            p["source"] = repo_url
        if not p.get("subdir"):
            p["subdir"] = p.get("path", "").lstrip("./") or p.get("name", "")
    return raw


# ── Routes ──────────────────────────────────────────────────────


@router.get("/installed")
async def list_installed(_user: dict = Depends(require_auth)):
    return await _scan_installed()


# ── Import plugin from GitHub (same pattern as skill import) ───


@router.post("/import", status_code=201)
async def import_plugin_from_github(
    body: ImportRequest,
    _user: dict = Depends(require_founder),
):
    """Import a plugin from a GitHub URL — file-by-file via Contents API, mirroring skill import.

    Writes files to plugin_repo_path/{plugin_name}/ instead of the DB.
    """
    owner, repo, branch, subpath = _parse_github_url(body.url)
    headers = _github_headers(_user)

    plugin_name = subpath.split("/")[-1] if subpath else repo

    root = _plugin_root()
    dest = root / plugin_name
    if dest.exists():
        raise HTTPException(status_code=409, detail=f"Plugin '{plugin_name}' already installed")

    api_url = f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{subpath}".rstrip("/")
    resp = http_requests.get(api_url, headers=headers, timeout=15, verify=False)
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="GitHub path not found")
    resp.raise_for_status()

    contents = resp.json()
    if not isinstance(contents, list):
        contents = [contents]

    files_to_import: list[dict] = []
    _recurse_github_dir(headers, owner, repo, contents, subpath, files_to_import, max_files=128)
    if not files_to_import:
        raise HTTPException(status_code=400, detail="No importable files found at URL")

    # Write files to disk
    dest.mkdir(parents=True, exist_ok=True)
    for f_info in files_to_import:
        file_path = dest / f_info["path"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(f_info["content"], encoding="utf-8")
        _logger.info("plugin file written: %s", file_path.relative_to(root))

    # Validate plugin.json exists
    manifest = _read_plugin_json(dest)
    if not manifest:
        shutil.rmtree(dest, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail="No .claude-plugin/plugin.json found in the imported files",
        )

    # Remove .git if any (shouldn't normally happen via Contents API, but just in case)
    git_dir = dest / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir, ignore_errors=True)

    _logger.info("plugin imported: %s -> %s (%d files)", body.url, dest, len(files_to_import))
    return {
        "ok": True,
        "name": plugin_name,
        "path": str(dest),
        "files": len(files_to_import),
    }


# ── Marketplace ─────────────────────────────────────────────────


@router.get("/marketplace")
async def get_marketplace(_user: dict = Depends(require_auth)):
    repo_url = _read_marketplace_repo_url()
    if not repo_url:
        return MarketPlaceStatus(imported=False)

    mkt_plugins = _read_marketplace_json()
    installed = {p["name"] for p in await _scan_installed()}

    plugins: list[PluginInfo] = []
    for entry in mkt_plugins:
        plugins.append(PluginInfo(
            name=entry.get("name", ""),
            version=entry.get("version", "0.0.0"),
            description=entry.get("description"),
            author=entry.get("author"),
            source_url=entry.get("source", repo_url),
            subdir=entry.get("subdir") or entry.get("path", "").lstrip("./"),
            commands=entry.get("commands", []),
            skills=entry.get("skills", []),
            agents=entry.get("agents", []),
            installed=entry.get("name", "") in installed,
        ))
    return MarketPlaceStatus(imported=True, repo_url=repo_url, plugins=plugins)


@router.post("/marketplace/import", status_code=201)
async def import_marketplace(
    body: ImportRequest,
    _user: dict = Depends(require_founder),
):
    """Import marketplace.json from a GitHub repo via API — same pattern as skill import."""
    owner, repo, branch, _ = _parse_github_url(body.url)
    repo_url = f"https://github.com/{owner}/{repo}"
    headers = _github_headers(_user)

    # Try root, then .claude-plugin/
    raw_json: dict | None = None
    for path in ("marketplace.json", ".claude-plugin/marketplace.json"):
        api_url = f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{path}?ref={branch}"
        resp = http_requests.get(api_url, headers=headers, timeout=15, verify=False)
        if resp.status_code == 404:
            continue
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "content" in data:
            import base64
            content = base64.b64decode(data["content"]).decode("utf-8")
            raw_json = json.loads(content)
            _logger.info("marketplace: found at %s", path)
            break

    if raw_json is None:
        raise HTTPException(
            status_code=400,
            detail="仓库中未找到 marketplace.json（检查根目录或 .claude-plugin/ 目录）",
        )

    # Normalize: accept both "source"/"subdir" and "path" fields
    plugins = raw_json.get("plugins", []) if isinstance(raw_json, dict) else []
    if isinstance(raw_json, list):
        plugins = raw_json
    for p in plugins:
        if not p.get("source"):
            p["source"] = repo_url
        if p.get("path") and not p.get("subdir"):
            p["subdir"] = p["path"].lstrip("./")
        elif not p.get("subdir"):
            p["subdir"] = p.get("name", "")

    # Write to cache
    cache_dir = _marketplace_dir()
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "marketplace.json").write_text(json.dumps({"plugins": plugins}, indent=2, ensure_ascii=False), encoding="utf-8")
    _save_marketplace_meta(repo_url)

    _logger.info("marketplace imported: %s (%d plugins)", repo_url, len(plugins))
    return {"ok": True, "repo_url": repo_url, "plugins_count": len(plugins)}


@router.delete("/marketplace")
async def remove_marketplace(
    _user: dict = Depends(require_founder),
):
    d = _marketplace_dir()
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    return {"ok": True}


@router.post("/marketplace/install/{plugin_name}", status_code=201)
async def install_from_marketplace(
    plugin_name: str,
    _user: dict = Depends(require_founder),
):
    """Install a plugin from marketplace — file-by-file via Contents API, mirroring skill import."""
    root = _plugin_root()
    mkt_plugins = _read_marketplace_json()
    entry = next((p for p in mkt_plugins if p.get("name") == plugin_name), None)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found in marketplace")

    source_url = entry.get("source")
    subdir = entry.get("subdir") or entry.get("path", "").lstrip("./")
    if not subdir:
        raise HTTPException(status_code=400, detail=f"Plugin '{plugin_name}' missing subdir/path in marketplace.json")
    # If no explicit source, use the marketplace repo URL
    if not source_url:
        source_url = _read_marketplace_repo_url()
    if not source_url:
        raise HTTPException(status_code=400, detail=f"Plugin '{plugin_name}' missing source in marketplace.json")

    dest = root / plugin_name
    if dest.exists():
        raise HTTPException(status_code=409, detail=f"Plugin '{plugin_name}' already installed")

    owner, repo, branch, _ = _parse_github_url(source_url)
    headers = _github_headers(_user)

    api_url = f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{subdir}?ref={branch}"
    resp = http_requests.get(api_url, headers=headers, timeout=15, verify=False)
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail=f"GitHub path not found: {subdir}")
    resp.raise_for_status()

    contents = resp.json()
    if not isinstance(contents, list):
        contents = [contents]

    files_to_import: list[dict] = []
    _recurse_github_dir(headers, owner, repo, contents, subdir, files_to_import, max_files=128)
    if not files_to_import:
        raise HTTPException(status_code=400, detail="No importable files found")

    dest.mkdir(parents=True, exist_ok=True)
    for f_info in files_to_import:
        file_path = dest / f_info["path"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(f_info["content"], encoding="utf-8")

    manifest = _read_plugin_json(dest)
    if not manifest:
        shutil.rmtree(dest, ignore_errors=True)
        raise HTTPException(status_code=400, detail="No .claude-plugin/plugin.json found")

    _logger.info("plugin installed from marketplace: %s (%d files)", plugin_name, len(files_to_import))
    return {"ok": True, "name": plugin_name, "path": str(dest), "files": len(files_to_import)}


# ── Uninstall / Update / Enable / Disable ──────────────────────


@router.post("/{name}/uninstall")
async def uninstall_plugin(
    name: str,
    _user: dict = Depends(require_founder),
):
    root = _plugin_root()
    dest = root / name
    if not dest.is_dir():
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")
    shutil.rmtree(dest, ignore_errors=True)
    return {"ok": True}


@router.post("/{name}/enable")
async def enable_plugin(
    name: str,
    _user: dict = Depends(require_founder),
):
    root = _plugin_root()
    dest = root / name
    if not dest.is_dir():
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")
    marker = dest / ".disabled"
    if marker.exists():
        marker.unlink()
    return {"ok": True, "enabled": True}


@router.post("/{name}/disable")
async def disable_plugin(
    name: str,
    _user: dict = Depends(require_founder),
):
    root = _plugin_root()
    dest = root / name
    if not dest.is_dir():
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")
    (dest / ".disabled").touch()
    return {"ok": True, "enabled": False}
