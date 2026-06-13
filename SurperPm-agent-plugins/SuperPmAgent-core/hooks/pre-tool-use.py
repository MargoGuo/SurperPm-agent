"""SuperPmAgent pre-tool hook.

This lightweight hook keeps the protocol stable while the W2 extension
resolver is wired in. It reads JSON from stdin and returns a permissive
response with optional metadata for downstream tracing.
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


def _extension_index_exists() -> bool:
    return (_marketplace_root() / "knowledge" / "extensions" / "INDEX.md").exists()


def main() -> None:
    payload = _read_payload()
    response = {
        "continue": True,
        "SuperPmAgent": {
            "hook": "pre-tool-use",
            "target": payload.get("tool_name") or payload.get("target"),
            "extension_index_available": _extension_index_exists(),
        },
    }
    print(json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()
