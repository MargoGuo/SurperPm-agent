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

import asyncio
import json
import logging
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.models.goal import Goal
from app.models.workspace import Workspace
from app.services.crypto import decrypt

_logger = logging.getLogger(__name__)

_REPOS_ROOT = Path("data/repos")
_PLUGIN_SUBDIRS = ("SuperPmAgent-core", "SuperPmAgent-coding", "SuperPmAgent-business")

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


def resolve_repo_url(goal: Goal, workspace: Workspace) -> str:
    """Pick the repo to operate on: goal > workspace > first of repos JSON."""
    candidates: list[str | None] = [goal.repo_url, workspace.repo_url]
    for raw in (goal.repos, workspace.repos):
        if not raw:
            continue
        try:
            arr = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if isinstance(arr, list) and arr:
            candidates.append(str(arr[0]))
    for c in candidates:
        if c and c.strip():
            return c.strip()
    raise RuntimeError("No repo_url configured on goal or workspace")


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


async def resolve_ssh_private_key_enc(workspace: Workspace) -> str | None:
    """The SSH key the user registers on GitHub is the global one; fall back to workspace."""
    from app.database import async_session
    from app.models.global_config import GlobalConfig

    async with async_session() as session:
        cfg = await session.get(GlobalConfig, 1)
    if cfg and cfg.ssh_private_key_enc:
        return cfg.ssh_private_key_enc
    return workspace.ssh_private_key_enc


def prepare_ssh(private_key_enc: str | None, keydir: Path) -> tuple[Path | None, str | None]:
    """Decrypt the private key to a 0600 keyfile, return (keyfile, GIT_SSH_COMMAND)."""
    if not private_key_enc:
        return None, None
    try:
        private_key = decrypt(private_key_enc)
    except Exception as e:
        raise RuntimeError(f"Failed to decrypt SSH key: {e}") from e

    keydir.mkdir(parents=True, exist_ok=True)
    keyfile = keydir / "id_ed25519"
    keyfile.write_text(private_key if private_key.endswith("\n") else private_key + "\n")
    keyfile.chmod(0o600)
    git_ssh = (
        f"ssh -i {keyfile} -o IdentitiesOnly=yes "
        "-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null"
    )
    return keyfile, git_ssh


async def _git(*args: str, env: dict[str, str]) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, **env},
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {stderr.decode().strip()}")
    return stdout.decode()


async def _default_branch(dest: Path, env: dict[str, str]) -> str:
    try:
        await _git("-C", str(dest), "remote", "set-head", "origin", "-a", env=env)
        ref = await _git(
            "-C", str(dest), "symbolic-ref", "--short", "refs/remotes/origin/HEAD", env=env
        )
        name = ref.strip().split("/")[-1]
        return name or "main"
    except RuntimeError:
        return "main"


async def clone_or_pull(ssh_url: str, dest: Path, env: dict[str, str]) -> str:
    """Clone the repo, or fetch+reset an existing clone. Returns the default branch name."""
    if (dest / ".git").is_dir():
        _logger.info("exec_env: fetching %s", dest)
        await _git("-C", str(dest), "fetch", "--all", "--prune", env=env)
        branch = await _default_branch(dest, env)
        await _git("-C", str(dest), "checkout", "-B", branch, f"origin/{branch}", env=env)
        await _git("-C", str(dest), "reset", "--hard", f"origin/{branch}", env=env)
        return branch

    _logger.info("exec_env: cloning %s → %s", ssh_url, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    await _git("clone", ssh_url, str(dest), env=env)
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


def plugin_dirs() -> list[str]:
    """Resolve local SuperPmAgent-plugins plugin dirs for `--plugin-dir`."""
    root = settings.plugin_repo_path
    if not root:
        _logger.info("exec_env: plugin_repo_path not configured — running without plugins")
        return []
    base = Path(root)
    dirs: list[str] = []
    for sub in _PLUGIN_SUBDIRS:
        d = base / sub
        if (d / ".disabled").exists():
            _logger.info("exec_env: skipping disabled plugin: %s", sub)
            continue
        if (d / ".claude-plugin" / "plugin.json").is_file():
            dirs.append(str(d))
        else:
            _logger.warning("exec_env: plugin dir missing or invalid: %s", d)
    return dirs


def workdir_for(workspace_id: str, goal_id: int) -> Path:
    return _REPOS_ROOT / workspace_id / f"goal-{goal_id}"


async def prepare_execution(goal: Goal, workspace: Workspace) -> ExecEnv:
    """Clone the goal's repo via SSH and assemble env + plugin dirs for the agent."""
    assert goal.id is not None
    repo_url = resolve_repo_url(goal, workspace)
    ssh_url = to_ssh_url(repo_url)
    workdir = workdir_for(workspace.id, goal.id)
    keydir = workdir.parent / f"goal-{goal.id}-ssh"

    key_enc = await resolve_ssh_private_key_enc(workspace)
    keyfile, git_ssh = prepare_ssh(key_enc, keydir)
    if not git_ssh:
        raise RuntimeError(
            "No SSH key configured (global or workspace) — required for git clone/push"
        )

    env: dict[str, str] = {"GIT_SSH_COMMAND": git_ssh}
    token = await resolve_github_token()
    if token:
        env["GH_TOKEN"] = token
        env["GITHUB_TOKEN"] = token

    branch = await clone_or_pull(ssh_url, workdir, env)

    return ExecEnv(
        workdir=workdir,
        env=env,
        plugins=plugin_dirs(),
        keydir=keydir if keyfile else None,
        branch_hint=branch,
    )


def cleanup_keydir(keydir: Path | None) -> None:
    """Remove the temporary SSH keyfile dir so credentials don't linger on disk."""
    if keydir and keydir.exists():
        shutil.rmtree(keydir, ignore_errors=True)
