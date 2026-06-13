"""GitHub API wrapper — PyGithub for existing + requests for new functions."""
import logging

import requests
from github import Auth, Github, GithubException, UnknownObjectException

_logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"


def _get_client(token: str) -> Github:
    return Github(auth=Auth.Token(token))


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


# ── Existing functions (PyGithub) ──────────────────────────────


def get_user_info(token: str) -> dict:
    """Return {username, avatar_url} for the authenticated user."""
    user = _get_client(token).get_user()
    return {"username": user.login, "avatar_url": user.avatar_url}


def list_user_repos(token: str) -> list[dict]:
    """Return repos the user owns or has access to, sorted by last pushed."""
    repos = _get_client(token).get_user().get_repos(sort="updated", direction="desc")
    result = []
    for repo in repos[:100]:
        result.append({
            "name": repo.name,
            "owner": repo.owner.login,
            "private": repo.private,
            "desc": repo.description or "",
            "updated": repo.pushed_at.isoformat() if repo.pushed_at else "",
            "stars": repo.stargazers_count,
        })
    return result


def validate_repo_access(token: str, owner: str, repo_name: str) -> bool:
    """Check whether the token can access a specific repo."""
    try:
        _get_client(token).get_repo(f"{owner}/{repo_name}")
        return True
    except (UnknownObjectException, GithubException):
        return False


# ── New functions (direct requests — avoid PyGithub quirks) ────


def get_repo_languages(token: str, owner: str, repo: str) -> dict[str, int]:
    """Return {language: bytes_of_code} for the repo via REST API."""
    r = requests.get(
        f"{_GITHUB_API}/repos/{owner}/{repo}/languages",
        headers=_headers(token),
        timeout=10,
    )
    r.raise_for_status()
    return r.json()  # {"Python": 12345, "TypeScript": 6789}


def get_repo_collaborators(token: str, owner: str, repo: str) -> list[dict]:
    """Return [{login, avatar_url}] for repo collaborators."""
    r = requests.get(
        f"{_GITHUB_API}/repos/{owner}/{repo}/collaborators",
        headers=_headers(token),
        timeout=10,
        params={"per_page": 20},
    )
    if r.status_code == 403:
        _logger.warning("No permission to list collaborators for %s/%s", owner, repo)
        return []
    r.raise_for_status()
    return [{"login": u["login"], "avatar_url": u["avatar_url"]} for u in r.json()]


def get_repo_info(token: str, owner: str, repo: str) -> dict:
    """Return basic repo metadata."""
    r = requests.get(
        f"{_GITHUB_API}/repos/{owner}/{repo}",
        headers=_headers(token),
        timeout=10,
    )
    r.raise_for_status()
    d = r.json()
    return {
        "description": d.get("description") or "",
        "topics": d.get("topics", []),
        "default_branch": d.get("default_branch", "main"),
    }


def read_file_from_repo(token: str, owner: str, repo: str, path: str) -> str | None:
    """Read a file's decoded content. Returns None if not found."""
    r = requests.get(
        f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
        headers=_headers(token),
        timeout=10,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    import base64
    data = r.json()
    if isinstance(data, list):
        return None
    return base64.b64decode(data["content"]).decode("utf-8")


def commit_file(
    token: str,
    owner: str,
    repo: str,
    path: str,
    content: str,
    message: str,
) -> dict:
    """Create or update a file in the repo."""
    import base64
    import json

    encoded = base64.b64encode(content.encode("utf-8")).decode()
    url = f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{path}"

    # Check if file exists to get its SHA
    existing_sha = None
    r = requests.get(url, headers=_headers(token), timeout=10)
    if r.status_code == 200:
        data = r.json()
        if not isinstance(data, list):
            existing_sha = data["sha"]

    body = {"message": message, "content": encoded}
    if existing_sha:
        body["sha"] = existing_sha

    r = requests.put(url, headers=_headers(token), json=body, timeout=10)
    r.raise_for_status()
    result = r.json()
    return {"sha": result["commit"]["sha"], "url": result["commit"]["html_url"]}
