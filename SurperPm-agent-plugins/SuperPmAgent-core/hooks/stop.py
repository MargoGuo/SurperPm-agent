"""SuperPmAgent stop hook.

The hook preserves the Stop protocol and records whether distillation inputs
appear to be available. The actual PR creation remains a reviewed loop action.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    return payload if isinstance(payload, dict) else {"payload": payload}


def _marketplace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> None:
    payload = _read_payload()
    response = {
        "continue": True,
        "SuperPmAgent": {
            "hook": "stop",
            "session_id": payload.get("session_id"),
            "distill_skill_available": (
                _marketplace_root() / "SuperPmAgent-core" / "skills" / "distill" / "SKILL.md"
            ).exists(),
        },
    }
    print(json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()
