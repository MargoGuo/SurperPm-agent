"""SuperPmAgent coding post-tool hook.

This hook keeps coding post-processing lightweight. It reports that an edit
occurred and leaves command selection to the explicit run-tests skill.
"""

from __future__ import annotations

import json
import sys
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


def main() -> None:
    payload = _read_payload()
    print(
        json.dumps(
            {
                "continue": True,
                "SuperPmAgent": {
                    "hook": "post-tool-use",
                    "tool": payload.get("tool_name"),
                    "next": "Run SuperPmAgent-run-tests before PR submission when edits affect behavior.",
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
