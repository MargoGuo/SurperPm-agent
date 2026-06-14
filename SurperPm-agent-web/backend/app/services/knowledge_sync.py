"""Knowledge repo sync — git clone / pull from remote.

Uses ``platform.run_cmd`` (subprocess on a thread) to avoid
NotImplementedError on Windows SelectorEventLoop configurations.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.config import settings
from app.services.platform import run_cmd

_logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path("knowledge")

_GIT_TIMEOUT = 30  # seconds


def _target_path() -> Path:
    return Path(settings.knowledge_repo_path) if settings.knowledge_repo_path else _DEFAULT_PATH


async def _create_conflict_goal(dest: Path, error_msg: str) -> None:
    """Auto-create a Goal when knowledge sync encounters a git conflict."""
    try:
        from app.services.goal_service import create_goal
        await create_goal(
            title="Knowledge sync conflict — resolve & push",
            description=(
                f"Knowledge repo `git pull --ff-only` failed.\n\n"
                f"**Repo**: `{dest}`\n\n"
                f"**Error**:\n```\n{error_msg[:500]}\n```\n\n"
                f"**Steps**:\n"
                f"1. `cd {dest}`\n"
                f"2. `git status` — check conflicting files\n"
                f"3. `git stash && git pull && git stash pop` or manual merge\n"
                f"4. `git add . && git commit && git push`\n\n"
                f"Use the built-in `code-review` skill to review changes before pushing."
            ),
            priority="high",
            source="knowledge_sync",
            dedup_key="Knowledge sync conflict",
        )
        _logger.info("knowledge_sync: created conflict resolution goal")
    except Exception:
        _logger.exception("knowledge_sync: failed to create conflict goal")


async def sync_knowledge_repo(clone_url: str, target_path: Path | None = None) -> bool:
    dest = target_path or _target_path()

    # ── Already a git repo → pull ──
    if (dest / ".git").is_dir():
        _logger.info("knowledge_sync: pulling %s", dest)
        try:
            await run_cmd("git", "-C", str(dest), "pull", "--ff-only", timeout=_GIT_TIMEOUT)
        except (RuntimeError, TimeoutError, OSError) as exc:
            _logger.warning("git pull failed: %s", exc)
            await _create_conflict_goal(dest, str(exc))
            return False
        _logger.info("knowledge_sync: pull ok")
        return True

    # ── Clone into a temp directory first, then swap —
    #     avoids nuking local data when network is down.
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.parent / f".knowledge-clone-{dest.name}"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)

    _logger.info("knowledge_sync: cloning %s → %s (tmp %s)", clone_url, dest, tmp)
    try:
        await run_cmd("git", "clone", clone_url, str(tmp), timeout=_GIT_TIMEOUT)
    except (RuntimeError, TimeoutError, OSError) as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        _logger.warning("git clone failed: %s", exc)
        return False

    # Swap: remove old (if any), rename tmp → dest
    if dest.is_dir():
        old = dest.parent / f".knowledge-old-{dest.name}"
        if old.exists():
            shutil.rmtree(old, ignore_errors=True)
        dest.rename(old)
        shutil.rmtree(old, ignore_errors=True)
    tmp.rename(dest)

    _logger.info("knowledge_sync: clone ok — %s", dest)
    return True


async def ensure_knowledge_cloned() -> Path | None:
    from app.database import async_session
    from app.models.global_config import GlobalConfig
    from app.services.crypto import decrypt
    from app.services.knowledge_store import get_store

    store = get_store()
    store_settings = store.get_settings()
    repo_url = store_settings.get("knowledge_repo_url", "")

    if not repo_url:
        async with async_session() as session:
            cfg = await session.get(GlobalConfig, 1)
            if cfg:
                repo_url = getattr(cfg, "knowledge_repo_url", "") or ""
    if not repo_url:
        _logger.debug("knowledge_sync: no knowledge_repo_url configured")
        return None

    token: str | None = None
    async with async_session() as session:
        cfg = await session.get(GlobalConfig, 1)
        if cfg and cfg.github_token_enc:
            try:
                token = decrypt(cfg.github_token_enc)
            except Exception:
                _logger.warning("knowledge_sync: failed to decrypt github_token_enc")

    if token and repo_url.startswith("https://"):
        clone_url = repo_url.replace("https://", f"https://{token}@")
    else:
        clone_url = repo_url

    dest = _target_path()
    ok = await sync_knowledge_repo(clone_url, dest)
    return dest if ok else None
