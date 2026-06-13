---
description: Run backend tests (pytest) and frontend type-check
---

Run tests for the project:

```bash
cd backend && uv run python -m pytest -v
```

If frontend exists and has tests configured:

```bash
cd frontend && pnpm typecheck
```

Report results clearly: how many passed, how many failed, and show failure details if any.
