"""Cross-platform utilities — single source of truth for OS differences.

All platform-specific logic (Windows vs Unix) lives here. Business code
imports symbols from this module instead of checking ``os.name`` / ``sys.platform``.

Subprocess: ``run_cmd`` delegates to a thread so it works on every platform
regardless of the event-loop policy (Selector or Proactor).
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
from pathlib import Path

_logger = logging.getLogger(__name__)

IS_WIN = os.name == "nt"
"""True on Windows, False on macOS / Linux."""

NULL_DEVICE = "NUL" if IS_WIN else "/dev/null"
"""Platform-appropriate null device for redirects."""

_DEFAULT_CMD_TIMEOUT = 120  # seconds


# ── Terminal support ───────────────────────────────────────────────


def supports_terminal() -> bool:
    """Whether the platform supports the terminal WebSocket (pty-based)."""
    return not IS_WIN


# ── Filesystem helpers ──────────────────────────────────────────────


def remove_dir(path: str | Path) -> None:
    """Remove a directory, handling Windows read-only files via icacls first."""
    if IS_WIN:
        subprocess.run(
            ["icacls", str(path), "/reset", "/t", "/q"],
            capture_output=True, text=True, timeout=15,
        )
    shutil.rmtree(str(path), ignore_errors=True)


def set_key_permissions(keyfile: str | Path) -> None:
    """Set restrictive permissions on an SSH key file (0o600 equivalent).

    On Windows this uses icacls to remove inherited permissions and grant
    read-only access to the current user.  On Unix it is a straightforward
    ``chmod 0o600``.
    """
    keypath = str(keyfile)
    if IS_WIN:
        username = os.environ.get("USERNAME", "")
        subprocess.run(
            ["icacls", keypath, "/inheritance:r", "/grant", f"{username}:(R)"],
            capture_output=True, text=True, timeout=10,
        )
        subprocess.run(
            [
                "icacls", keypath, "/remove",
                "BUILTIN\\Users",
                "NT AUTHORITY\\SYSTEM",
                "NT AUTHORITY\\Authenticated Users",
            ],
            capture_output=True, text=True, timeout=10,
        )
    else:
        os.chmod(keypath, 0o600)


# ── Tool discovery ──────────────────────────────────────────────────


def find_ssh_keygen() -> str:
    """Find a working ssh-keygen binary.

    On Windows prefers the built-in OpenSSH client (System32\\OpenSSH)
    over Git-for-Windows' bundled copy, because the latter may produce
    keys that are incompatible with the native ssh client.
    """
    if IS_WIN:
        win_openssh = (
            Path(os.environ.get("SystemRoot", "C:\\Windows"))
            / "System32"
            / "OpenSSH"
            / "ssh-keygen.exe"
        )
        if win_openssh.is_file():
            return str(win_openssh)
    which = shutil.which("ssh-keygen")
    if which:
        return which
    raise RuntimeError("ssh-keygen not found on the system")


# ── Subprocess ──────────────────────────────────────────────────────


async def run_cmd(
    *args: str,
    cwd: str | Path | None = None,
    timeout: int = _DEFAULT_CMD_TIMEOUT,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> str:
    """Run a command on a thread — works on every platform and event loop.

    Returns the captured stdout (stripped).  When *check* is True raises
    ``RuntimeError`` on non-zero exit codes; when False the caller must
    inspect the return value.
    """

    def _run() -> str:
        proc = subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
            env={**os.environ, **(env or {})},
        )
        if check and proc.returncode != 0:
            raise RuntimeError(
                f"Command '{' '.join(args)}' failed (rc={proc.returncode}): "
                f"{proc.stderr.strip()}"
            )
        return proc.stdout.strip()

    return await asyncio.to_thread(_run)
