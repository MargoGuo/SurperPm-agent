---
name: SuperPmAgent-submit-pr
description: Create a concise GitHub pull request from a verified change and include loop evidence in the PR body.
argument-hint: "target repository path and PR summary"
---

# Submit PR

Open a reviewable PR only after the run has verification evidence.

## Preconditions

- Target repository path is confirmed.
- Working tree changes match the accepted scope.
- Relevant checks have passed, or blockers are documented.
- No secrets or local absolute paths are included.

## Process

1. Inspect git status and diff.
2. Create a focused branch if needed.
3. Commit only relevant files.
4. Push the branch.
5. Open a PR with summary, test plan, and SuperPmAgent loop evidence.

## PR Body

```markdown
## Summary
- 

## Test plan
- 

## SuperPmAgent evidence
- Goal:
- Session:
- Skills used:
- Known risks:
```

Do not force push or bypass hooks unless a human explicitly approves it.
