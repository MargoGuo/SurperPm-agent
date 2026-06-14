#!/usr/bin/env python3
"""Safe stop hook for SuperPmAgent-core.

The web runner and benchmark harness need a reliable end-of-loop signal. This
hook must not turn a finished delivery into an unexpected second task by default.
It returns structured SuperPmAgent metadata that downstream systems can persist or use
to start distillation explicitly.
"""
import json
import os
import re
import sys


def _read_payload() -> dict:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    return payload if isinstance(payload, dict) else {"payload": payload}


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]", "-", value.lower())
    return re.sub(r"-+", "-", slug).strip("-")[:50] or "goal"


def _status(payload: dict) -> str:
    explicit = str(payload.get("status") or "").strip().lower()
    if explicit:
        return explicit
    if payload.get("error") or payload.get("failure_reason"):
        return "failed"
    if payload.get("pr_url") or payload.get("commit") or payload.get("branch"):
        return "completed"
    return "unknown"


def _metadata(payload: dict) -> dict:
    session = str(payload.get("session") or payload.get("session_name") or "unknown")
    status = _status(payload)
    tests_passed = payload.get("tests_passed")
    verification_state = (
        "passed" if tests_passed is True else
        "failed" if tests_passed is False else
        "unknown"
    )
    return {
        "hook": "stop",
        "status": status,
        "session": session,
        "goal": payload.get("goal") or payload.get("goal_id") or "unknown",
        "pr_url": payload.get("pr_url") or "",
        "commit": payload.get("commit") or "",
        "branch": payload.get("branch") or "",
        "verification": verification_state,
        "failure_phase": payload.get("failure_phase") or "",
        "failure_reason": payload.get("failure_reason") or payload.get("error") or "",
        "distill_recommended": status in {"completed", "success", "failed", "blocked"},
        "distill_branch_hint": f"distill/auto-{_safe_slug(session)}",
        "next": "Run /SuperPmAgent-core:distill summary <session> or auto-distill from persisted execution evidence.",
    }


def _optional_self_heal(payload: dict) -> dict | None:
    if not _truthy(os.getenv("SUPERPMAGENT_STOP_HOOK_SELF_HEAL", "")):
        return None
    tests_passed = payload.get("tests_passed", True)
    iterations = int(payload.get("iterations") or 0)
    max_iterations = int(payload.get("max_iterations") or 3)
    if tests_passed is not False or iterations >= max_iterations:
        return None
    return {
        "continue": True,
        "user_message": (
            f"Tests failed on iteration {iterations + 1}/{max_iterations}.\n\n"
            f"First failure:\n{payload.get('test_output') or payload.get('failure_reason') or 'unknown'}\n\n"
            "Use SuperPmAgent-coding/debugger for one focused fix attempt, then rerun the failing check."
        ),
        "SuperPmAgent": _metadata(payload),
    }


def main() -> int:
    payload = _read_payload()
    result = _optional_self_heal(payload)
    if result is None:
        result = {"continue": False, "SuperPmAgent": _metadata(payload)}
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
