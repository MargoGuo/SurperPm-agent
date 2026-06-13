---
name: SuperPmAgent-run-tests
description: Discover and run the appropriate Conduit lint, test, typecheck, and build commands for a completed code change.
argument-hint: "target repository path and changed files"
---

# Run Tests

Run checks that prove the change is ready for review.

## Process

1. Read package scripts and existing CI configuration.
2. Choose checks based on changed files.
3. Run the narrowest relevant checks first.
4. Run broader checks before PR submission when time allows.
5. Capture command, exit code, and the first real failure if any command fails.

## Check Selection

- Frontend-only L1 task: frontend lint, relevant component tests, build if available.
- Backend-only task: backend lint and backend unit tests.
- Cross-stack task: backend tests, frontend tests, and build/type checks.
- PR-ready path: use the same checks expected by CI.

## Output

```text
Commands Run:
- command:
  result:
First Failure:
Coverage:
Ready For PR: yes | no
```

Do not mark a run ready if checks were skipped without an explicit blocker.
