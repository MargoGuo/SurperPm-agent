---
description: Run linters (backend ruff + frontend eslint/typecheck)
---

Run all linters:

**Backend:**
```bash
cd backend && uv run ruff check . && uv run ruff format --check .
```

**Frontend (if exists):**
```bash
cd frontend && pnpm lint && pnpm typecheck
```

Fix any auto-fixable issues with `ruff check --fix` or `pnpm lint --fix`. Report remaining issues.
