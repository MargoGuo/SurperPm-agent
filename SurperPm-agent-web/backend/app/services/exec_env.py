"""Execution environment prep for goal runs.

Before invoking the `/goal` plugin command, a goal execution needs:
  - the goal's repo cloned (via SSH using the workspace private key),
  - git/gh credentials injected into the agent's env,
  - the local SuperPmAgent-plugins directories resolved for `--plugin-dir`.

The `/goal` command (and its `submit-pr` skill) assume the repo is already
cloned and credentials are already present in the environment, so all of that
is set up here first.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.services.crypto import decrypt
from app.services.platform import NULL_DEVICE, remove_dir, run_cmd, set_key_permissions

_logger = logging.getLogger(__name__)

# Place repos outside the backend directory so uvicorn --reload does not
# trigger on git clone/pull during goal execution.
# Resolved relative to this file so it is independent of the process CWD:
#   app/services/exec_env.py → ../../../data/repos  (project-root/data/repos)
_REPOS_ROOT = (Path(__file__).resolve().parent.parent.parent.parent / "data" / "repos").resolve()
_SSH_PREFIX = re.compile(r"^(git@|ssh://)")
_HTTPS_REPO = re.compile(r"^https?://(?:[^@/]+@)?([^/]+)/(.+?)(?:\.git)?/?$")
_SHORT_REPO = re.compile(r"^[\w.-]+/[\w.-]+?(?:\.git)?/?$")


@dataclass
class ExecEnv:
    """Prepared execution context for a goal run."""

    workdir: Path
    env: dict[str, str] = field(default_factory=dict)
    plugins: list[str] = field(default_factory=list)
    keydir: Path | None = None
    branch_hint: str = "main"


def resolve_repo_url(goal: dict, workspace: dict) -> str:
    """Pick the repo to operate on: goal > workspace > first of repos JSON."""
    candidates: list[str | None] = [
        goal.get("repo_url"),
        workspace.get("repo_url"),
    ]
    for raw in (goal.get("repos"), workspace.get("repos")):
        if not raw:
            continue
        try:
            arr = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            continue
        if isinstance(arr, list) and arr:
            candidates.append(str(arr[0]))
    for c in candidates:
        if c and c.strip():
            return c.strip()
    return ""


def to_ssh_url(url: str) -> str:
    """Normalize a repo URL to scp-style SSH form. Accepts https / ssh / owner/repo."""
    if _SSH_PREFIX.match(url):
        return url
    m = _HTTPS_REPO.match(url)
    if m:
        host, path = m.group(1), m.group(2)
        return f"git@{host}:{path}.git"
    if _SHORT_REPO.match(url):
        path = url.rstrip("/")
        if not path.endswith(".git"):
            path += ".git"
        return f"git@github.com:{path}"
    return url


async def resolve_ssh_private_key_enc(workspace: dict) -> str | None:
    """Workspace-level SSH key takes priority, fallback to global."""
    # Workspace key first (more specific)
    ws_key = workspace.get("ssh_private_key_enc")
    if ws_key:
        return ws_key
    # Global key as fallback
    from app.database import async_session
    from app.models.global_config import GlobalConfig

    async with async_session() as session:
        cfg = await session.get(GlobalConfig, 1)
    if cfg and cfg.ssh_private_key_enc:
        return cfg.ssh_private_key_enc
    return None


def prepare_ssh(private_key_enc: str | None, keydir: Path) -> tuple[Path | None, str | None]:
    """Decrypt the private key to a 0600 keyfile, return (keyfile, GIT_SSH_COMMAND)."""
    if not private_key_enc:
        return None, None
    try:
        private_key = decrypt(private_key_enc)
    except Exception as e:
        raise RuntimeError(f"Failed to decrypt SSH key: {e}") from e

    # Nuke stale keydir — icacls may have locked previous keyfiles as read-only
    if keydir.exists():
        remove_dir(keydir)
    keydir.mkdir(parents=True, exist_ok=True)
    keyfile = keydir / "id_ed25519"
    keyfile.write_text(private_key if private_key.endswith("\n") else private_key + "\n")
    set_key_permissions(keyfile)
    git_ssh = (
        f"ssh -i {keyfile} -o IdentitiesOnly=yes "
        f"-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile={NULL_DEVICE}"
    )
    return keyfile, git_ssh


async def _default_branch(dest: Path, env: dict[str, str]) -> str:
    try:
        await run_cmd("git", "-C", str(dest), "remote", "set-head", "origin", "-a", env=env)
        ref = await run_cmd(
            "git", "-C", str(dest), "symbolic-ref", "--short", "refs/remotes/origin/HEAD", env=env,
        )
        name = ref.strip().split("/")[-1]
        return name or "main"
    except RuntimeError:
        return "main"


async def clone_or_pull(ssh_url: str, dest: Path, env: dict[str, str]) -> str:
    """Clone the repo, or fetch+reset an existing clone. Returns the default branch name."""
    if (dest / ".git").is_dir():
        _logger.info("exec_env: fetching %s", dest)
        # Force remote to SSH — may have been previously cloned via HTTPS
        await run_cmd("git", "-C", str(dest), "remote", "set-url", "origin", ssh_url, env=env)
        await run_cmd("git", "-C", str(dest), "fetch", "--all", "--prune", env=env)
        branch = await _default_branch(dest, env)
        await run_cmd("git", "-C", str(dest), "checkout", "-B", branch, f"origin/{branch}", env=env)
        await run_cmd("git", "-C", str(dest), "reset", "--hard", f"origin/{branch}", env=env)
        return branch

    _logger.info("exec_env: cloning %s → %s", ssh_url, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    await run_cmd("git", "clone", ssh_url, str(dest), env=env)
    return await _default_branch(dest, env)


async def resolve_github_token() -> str | None:
    """Decrypt the global GitHub token (used by `gh` to open the PR)."""
    from app.database import async_session
    from app.models.global_config import GlobalConfig

    async with async_session() as session:
        cfg = await session.get(GlobalConfig, 1)
    if not cfg or not cfg.github_token_enc:
        _logger.info("exec_env: no global github_token configured")
        return None
    try:
        return decrypt(cfg.github_token_enc)
    except Exception:
        _logger.warning("exec_env: failed to decrypt github_token_enc")
        return None


def _resolve_plugin_root() -> Path | None:
    """Find the plugins directory: knowledge/plugins/ first, then fallback."""
    from app.services.knowledge_store import get_store

    store = get_store()
    knowledge_plugins = store._root.parent / "plugins"
    if knowledge_plugins.is_dir():
        return knowledge_plugins
    if settings.plugin_repo_path:
        p = Path(settings.plugin_repo_path)
        if p.is_dir():
            return p
    return None


def plugin_dirs() -> list[str]:
    """Resolve plugin dirs from knowledge/plugins/ for agent execution."""
    base = _resolve_plugin_root()
    if not base:
        _logger.info("exec_env: no plugin directory found")
        return []
    dirs: list[str] = []
    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if (d / ".disabled").exists():
            _logger.info("exec_env: skipping disabled plugin: %s", d.name)
            continue
        if (d / ".claude-plugin" / "plugin.json").is_file():
            dirs.append(str(d.resolve()))
    return dirs


def workdir_for(workspace_id: str, goal_id: int) -> Path:
    return _REPOS_ROOT / workspace_id / f"goal-{goal_id}"


async def prepare_execution(goal: dict, workspace: dict) -> ExecEnv:
    """Clone the goal's repo via SSH and assemble env + plugin dirs.

    If no repo is configured, uses a temporary work directory (no git clone).
    """
    goal_id = goal.get("id")
    assert goal_id is not None
    repo_url = resolve_repo_url(goal, workspace)
    workdir = workdir_for(workspace.get("id", ""), goal_id)

    env: dict[str, str] = {}
    token = await resolve_github_token()
    if token:
        env["GH_TOKEN"] = token
        env["GITHUB_TOKEN"] = token

    keydir = None
    branch = None

    if repo_url:
        ssh_url = to_ssh_url(repo_url)
        keydir = workdir.parent / f"goal-{goal_id}-ssh"
        key_enc = await resolve_ssh_private_key_enc(workspace)
        keyfile, git_ssh = prepare_ssh(key_enc, keydir)
        if git_ssh:
            env["GIT_SSH_COMMAND"] = git_ssh
        branch = await clone_or_pull(ssh_url, workdir, env)
    else:
        workdir.mkdir(parents=True, exist_ok=True)

    return ExecEnv(
        workdir=workdir,
        env=env,
        plugins=plugin_dirs(),
        keydir=keydir,
        branch_hint=branch,
    )


def cleanup_keydir(keydir: Path | None) -> None:
    """Remove the temporary SSH keyfile dir so credentials don't linger on disk."""
    if keydir and keydir.exists():
        remove_dir(keydir)
