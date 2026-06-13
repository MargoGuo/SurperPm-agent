---
description: Create a PR with team conventions
---

Before creating a PR:

1. Run tests: `cd backend && uv run python -m pytest -v`
2. Run lint: `cd backend && uv run ruff check .`
3. Ensure all pass

Then create the PR:

```bash
gh pr create --title "<type>(<scope>): <description>" --body "## Summary
- <what changed>

## Test plan
- [ ] Tests pass locally
- [ ] Lint clean"
```

Title format: `feat|fix|docs|refactor(<module>): imperative description`

Modules: backend, frontend, plan, infra
