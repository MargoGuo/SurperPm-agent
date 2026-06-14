"""Auth — OAuth (primary) + PAT fallback (login/logout/me).

SuperPmAgent does not have a user table. Session = itsdangerous-signed cookie
carrying the user's GitHub token + username + repo. Identity is implicit:
"if you can access the repo with this token, you can log in."
"""
import asyncio
import logging
import secrets
import time
from datetime import UTC, datetime
from typing import Annotated

import requests
from fastapi import APIRouter, Cookie, HTTPException, Query, Response
from fastapi.responses import HTMLResponse

from app.config import settings
from app.services import github_client
from app.services import session as session_svc
from app.services.crypto import encrypt

_logger = logging.getLogger(__name__)

router = APIRouter()

COOKIE_NAME = "SuperPmAgent_session"
COOKIE_MAX_AGE = 7 * 24 * 3600  # 7 days
OAUTH_STATE_COOKIE = "SuperPmAgent_oauth_state"
OAUTH_STATE_MAX_AGE = 600  # 10 minutes
FRONTEND_URL = settings.frontend_url


async def _ensure_knowledge_repo(repo: str, token: str, username: str = "") -> None:
    """Persist the login repo as the knowledge_repo_url + encrypt token.

    The first user to bind the repo becomes the founder.
    """
    from app.database import async_session
    from app.models.global_config import GlobalConfig
    from app.services.knowledge_store import get_store

    store = get_store()
    store_settings = store.get_settings()
    repo_url = f"https://github.com/{repo}".removesuffix(".git")

    if not store_settings.get("knowledge_repo_url"):
        await store.update_settings({"knowledge_repo_url": repo_url})

    async with async_session() as session:
        cfg = await session.get(GlobalConfig, 1)
        if not cfg:
            cfg = GlobalConfig(id=1)
            session.add(cfg)
        if username and not cfg.founder_username:
            cfg.founder_username = username
        cfg.github_token_enc = encrypt(token)
        cfg.updated_at = datetime.now(UTC)
        session.add(cfg)
        await session.commit()

    from app.services.knowledge_sync import ensure_knowledge_cloned
    asyncio.create_task(ensure_knowledge_cloned())


async def _global_config_snapshot() -> tuple[bool, str | None, str, str]:
    """Return (initialized, founder_username, repo 'owner/repo', anthropic_key)."""
    from app.database import async_session
    from app.models.global_config import GlobalConfig
    from app.services.crypto import decrypt
    from app.services.knowledge_store import get_store

    store = get_store()
    store_settings = store.get_settings()
    knowledge_repo_url = store_settings.get("knowledge_repo_url", "")

    async with async_session() as session:
        cfg = await session.get(GlobalConfig, 1)
        if not cfg:
            return False, None, "", ""
        repo = ""
        if knowledge_repo_url:
            repo = (
                knowledge_repo_url
                .replace("https://github.com/", "")
                .removesuffix(".git")
                .strip("/")
            )
        key = ""
        if cfg.ai_api_key_enc:
            try:
                key = decrypt(cfg.ai_api_key_enc)
            except Exception:
                key = ""
        return bool(knowledge_repo_url), cfg.founder_username, repo, key


def _post_with_retry(url: str, json: dict, max_retries: int = 3) -> requests.Response | None:
    """POST with retry on transient SSL/connection errors (proxy instability)."""
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            return requests.post(url, json=json, headers={"Accept": "application/json"}, timeout=10)
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            last_err = e
            if attempt < max_retries - 1:
                delay = (attempt + 1) * 1.5
                _logger.warning(
                    "Token exchange attempt %d failed (%s), retrying in %.1fs",
                    attempt + 1, e, delay,
                )
                time.sleep(delay)
    _logger.error("Token exchange failed after %d attempts: %s", max_retries, last_err)
    return None

# ============================================================
# PAT fallback (existing)
# ============================================================


@router.post("/pat/repos")
async def pat_repos(payload: dict) -> dict:
    """Validate a PAT and return the user info + accessible repos (no session set)."""
    pat = payload.get("pat", "").strip()
    if not pat:
        raise HTTPException(status_code=400, detail="pat required")

    try:
        user_info = github_client.get_user_info(pat)
    except Exception as exc:
        _logger.warning("PAT validation failed: %s", exc)
        raise HTTPException(
            status_code=401,
            detail=f"Invalid PAT or GitHub unreachable: {exc}",
        ) from None

    try:
        repos = github_client.list_user_repos(pat)
    except Exception:
        repos = []

    initialized, founder, _repo, _key = await _global_config_snapshot()
    return {
        "username": user_info["username"],
        "avatar_url": user_info.get("avatar_url", ""),
        "repos": repos,
        "initialized": initialized,
        "is_founder": bool(founder) and user_info["username"] == founder,
    }


@router.post("/login")
async def login(payload: dict, response: Response) -> dict:
    """Validate (pat, repo) by calling GitHub. On success, set session cookie."""
    pat = payload.get("pat", "").strip()
    repo = payload.get("repo", "").strip()
    anthropic_key = payload.get("anthropic_key", "").strip()
    if not pat:
        raise HTTPException(status_code=400, detail="pat required")

    # Second login (already initialized): non-founders just provide a token and
    # inherit the globally-configured repo + AI key.
    initialized, _founder, global_repo, global_key = await _global_config_snapshot()
    if not repo:
        if not (initialized and global_repo):
            raise HTTPException(status_code=400, detail="repo required")
        repo = global_repo
    if not anthropic_key:
        anthropic_key = global_key

    r = requests.get(
        f"https://api.github.com/repos/{repo}",
        headers={
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )

    if r.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Invalid PAT or no access to that repo",
        )

    # Get the authenticated user's info (not repo owner)
    try:
        user_info = github_client.get_user_info(pat)
        username = user_info["username"]
        avatar_url = user_info.get("avatar_url", "")
    except Exception:
        username = "unknown"
        avatar_url = ""
    cookie_value = session_svc.encode(
        {
            "github_token": pat,
            "repo": repo,
            "username": username,
            "avatar_url": avatar_url,
            "anthropic_key": anthropic_key,
        }
    )
    response.set_cookie(
        key=COOKIE_NAME,
        value=cookie_value,
        httponly=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
    )

    await _ensure_knowledge_repo(repo, pat, username)

    return {"ok": True, "username": username, "repo": repo, "profile_missing": not username}


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME)

    from app.database import async_session
    from app.models.global_config import GlobalConfig

    async with async_session() as session:
        cfg = await session.get(GlobalConfig, 1)
        if cfg and cfg.github_token_enc:
            cfg.github_token_enc = None
            session.add(cfg)
            await session.commit()

    return {"ok": True}


@router.get("/me")
async def me(
    SuperPmAgent_session: Annotated[str | None, Cookie()] = None,
) -> dict:
    """Return current logged-in user; 401 if no/invalid cookie."""
    if not SuperPmAgent_session:
        raise HTTPException(status_code=401, detail="not_logged_in")
    data = session_svc.decode(SuperPmAgent_session)
    if not data:
        raise HTTPException(status_code=401, detail="invalid_session")
    username = data.get("username", "")
    _initialized, founder, _repo, _key = await _global_config_snapshot()
    return {
        "username": username,
        "repo": data.get("repo", ""),
        "avatar_url": data.get("avatar_url", ""),
        "is_founder": bool(founder) and username == founder,
    }


# ============================================================
# GitHub OAuth
# ============================================================


@router.get("/github/authorize")
async def github_authorize(response: Response) -> dict:
    """Return the GitHub OAuth authorize URL. Sets a temporary state cookie."""
    client_id = settings.github_oauth_client_id
    redirect_uri = settings.github_oauth_redirect_uri
    if not client_id:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")

    state = secrets.token_urlsafe(32)
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        samesite="lax",
        max_age=OAUTH_STATE_MAX_AGE,
    )

    authorize_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=repo,read:org"
        f"&state={state}"
    )
    return {"url": authorize_url}


def _make_html_response(url: str) -> HTMLResponse:
    """Create an HTML page that does a client-side meta-refresh redirect.

    Uses 200 + JS redirect instead of 3xx so Vite's proxy forwards Set-Cookie headers.
    """
    body = (
        f"<!DOCTYPE html><html><head><meta http-equiv='refresh' content='0;url={url}'>"
        f"</head><body></body></html>"
    )
    response = HTMLResponse(content=body)
    response.headers["location"] = url
    return response


def _oauth_html_redirect(error: str) -> HTMLResponse:
    """Return an HTML redirect to the frontend login page with an error parameter."""
    response = _make_html_response(f"{FRONTEND_URL}/login?error={error}")
    response.delete_cookie(OAUTH_STATE_COOKIE)
    return response


@router.get("/github/callback")
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = Query(None),
    SuperPmAgent_oauth_state: Annotated[str | None, Cookie()] = None,
):
    """Handle the GitHub OAuth redirect. Exchange code for token, set session."""
    if error:
        return _oauth_html_redirect("access_denied")

    if not SuperPmAgent_oauth_state or SuperPmAgent_oauth_state != state:
        return _oauth_html_redirect("state_invalid")

    # Exchange code for access token (with retry for flaky proxy SSL)
    token_resp = _post_with_retry(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": settings.github_oauth_client_id,
            "client_secret": settings.github_oauth_client_secret,
            "code": code,
            "redirect_uri": settings.github_oauth_redirect_uri,
        },
    )

    if token_resp is None or token_resp.status_code != 200:
        return _oauth_html_redirect("oauth_failed")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return _oauth_html_redirect("oauth_failed")

    try:
        user_info = github_client.get_user_info(access_token)
        username = user_info["username"]
        avatar_url = user_info.get("avatar_url", "")
    except Exception:
        return _oauth_html_redirect("oauth_failed")

    cookie_value = session_svc.encode(
        {
            "github_token": access_token,
            "username": username,
            "avatar_url": avatar_url,
            "repo": "",
            "anthropic_key": "",
        }
    )

    response = _make_html_response(f"{FRONTEND_URL}/login?step=select")
    response.delete_cookie(OAUTH_STATE_COOKIE)
    response.set_cookie(
        key=COOKIE_NAME,
        value=cookie_value,
        httponly=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
    )
    return response


@router.get("/github/repos")
async def github_repos(
    SuperPmAgent_session: Annotated[str | None, Cookie()] = None,
) -> list[dict]:
    """List repos accessible with the OAuth token stored in session."""
    if not SuperPmAgent_session:
        raise HTTPException(status_code=401, detail="not_logged_in")
    data = session_svc.decode(SuperPmAgent_session)
    if not data:
        raise HTTPException(status_code=401, detail="invalid_session")

    token = data.get("github_token", "")
    if not token:
        raise HTTPException(status_code=401, detail="OAuth token not found in session")

    try:
        return github_client.list_user_repos(token)
    except Exception:
        return []


@router.post("/github/complete")
async def github_complete(
    payload: dict,
    response: Response,
    SuperPmAgent_session: Annotated[str | None, Cookie()] = None,
) -> dict:
    """Finalise OAuth login: validate repo access, store repo + API key in session."""
    if not SuperPmAgent_session:
        raise HTTPException(status_code=401, detail="not_logged_in")
    data = session_svc.decode(SuperPmAgent_session)
    if not data:
        raise HTTPException(status_code=401, detail="invalid_session")

    token = data.get("github_token", "")
    username = data.get("username", "")
    if not token:
        raise HTTPException(status_code=401, detail="OAuth token not found in session")

    repo = payload.get("repo", "").strip()
    anthropic_key = payload.get("anthropic_key", "").strip()

    # Second login (already initialized): non-founders inherit the global repo + key.
    initialized, _founder, global_repo, global_key = await _global_config_snapshot()
    if not repo:
        if not (initialized and global_repo):
            raise HTTPException(status_code=400, detail="repo required")
        repo = global_repo
    if not anthropic_key:
        anthropic_key = global_key

    # Parse "owner/repo"
    parts = repo.split("/")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="repo must be owner/repo format")

    if not github_client.validate_repo_access(token, parts[0], parts[1]):
        raise HTTPException(status_code=401, detail="Cannot access that repository")

    cookie_value = session_svc.encode(
        {
            "github_token": token,
            "username": username,
            "avatar_url": data.get("avatar_url", ""),
            "repo": repo,
            "anthropic_key": anthropic_key,
        }
    )
    response.set_cookie(
        key=COOKIE_NAME,
        value=cookie_value,
        httponly=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
    )

    await _ensure_knowledge_repo(repo, token, username)

    return {"ok": True, "username": username, "repo": repo, "profile_missing": not username}
