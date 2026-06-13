---
name: SuperPmAgent-coding
description: Implement a scoped code change after repo exploration has identified target files and verification commands.
argument-hint: "implementation plan"
---

# Coding

Implement the smallest change that satisfies the accepted scope.

## Required Before Editing

- Goal snapshot.
- Candidate files from `repo-explorer`.
- Planned edits.
- Planned checks.
- Known out-of-scope items.

## Process

1. Read target files before modifying them.
2. Preserve existing style and architecture.
3. Add or update tests when behavior changes.
4. Keep frontend, API, model, and persistence changes consistent for cross-stack tasks.
5. Record assumptions that should be verified by tests or review.

## Exit Criteria

- Changed files match the accepted scope.
- The verification plan is ready for `run-tests`.
- No unrelated refactors are included.
- No secrets or local machine paths are introduced.
