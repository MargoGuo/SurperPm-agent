"""Auth — OAuth (primary) + PAT fallback (login/logout/me).

SuperPmAgent does not have a user table. Session = itsdangerous-signed cookie
carrying the user's GitHub token + username + repo. Identity is implicit:
"if you can access the repo with this token, you can log in."
"""
import logging
import secrets
import time
from typing import Annotated

import requests
from fastapi import APIRouter, Cookie, HTTPException, Query, Response
from fastapi.responses import HTMLResponse

from app.config import settings
from app.services import session as session_svc
from app.services import github_client

_logger = logging.getLogger(__name__)

router = APIRouter()

COOKIE_NAME = "SuperPmAgent_session"
COOKIE_MAX_AGE = 7 * 24 * 3600  # 7 days
OAUTH_STATE_COOKIE = "SuperPmAgent_oauth_state"
OAUTH_STATE_MAX_AGE = 600  # 10 minutes
FRONTEND_URL = "http://localhost:5173"


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
                _logger.warning("Token exchange attempt %d failed (%s), retrying in %.1fs", attempt + 1, e, delay)
                time.sleep(delay)
    _logger.error("Token exchange failed after %d attempts: %s", max_retries, last_err)
    return None

# ============================================================
# PAT fallback (existing)
# ============================================================


@router.post("/login")
async def login(payload: dict, response: Response) -> dict:
    """Validate (pat, repo) by calling GitHub. On success, set session cookie."""
    pat = payload.get("pat", "").strip()
    repo = payload.get("repo", "").strip()
    anthropic_key = payload.get("anthropic_key", "").strip()
    if not pat or not repo or not anthropic_key:
        raise HTTPException(
            status_code=400, detail="pat, repo, and anthropic_key required"
        )

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

    repo_data = r.json()
    username = repo_data.get("owner", {}).get("login", "unknown")
    avatar_url = repo_data.get("owner", {}).get("avatar_url", "")
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

    return {"ok": True, "username": username, "repo": repo, "profile_missing": True}


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME)
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
    return {
        "username": data.get("username", ""),
        "repo": data.get("repo", ""),
        "avatar_url": data.get("avatar_url", ""),
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
        raise HTTPException(status_code=403, detail="Invalid state parameter")

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
    if not repo:
        raise HTTPException(status_code=400, detail="repo required")

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

    return {"ok": True, "username": username, "repo": repo, "profile_missing": True}
