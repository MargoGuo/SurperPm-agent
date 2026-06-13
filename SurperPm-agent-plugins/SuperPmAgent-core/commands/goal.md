---
description: Start a SuperPmAgent delivery loop from a PM goal or GitHub issue.
argument-hint: "[goal text or issue URL]"
allowed-tools: Read, Glob, Grep, Bash, TodoWrite
---

# SuperPmAgent Goal

You are starting one SuperPmAgent delivery loop.

## Inputs To Collect

- Goal text or issue URL.
- Target repository path or URL.
- Optional session folder under `knowledge/sessions/`.
- Constraints: max iterations, token budget, maximum duration, sandbox mode.

## Required Flow

1. Clarify only if the goal is ambiguous enough to block implementation.
2. Use `SuperPmAgent-core/find` to discover relevant skills and knowledge.
3. Ask `SuperPmAgent-coding/repo-explorer` to locate target files before editing.
4. Use the most specific `SuperPmAgent-business` skill when the change matches a known pattern.
5. Use `SuperPmAgent-coding/coding` for implementation.
6. Use `SuperPmAgent-coding/run-tests` for lint and test commands.
7. Use `SuperPmAgent-coding/debugger` for up to three focused fix rounds if checks fail.
8. Use `SuperPmAgent-coding/submit-pr` when the target repository is ready for review.
9. End with a compact loop summary and invoke distillation if the run produced reusable knowledge.

## Success Evidence

Return:

- Goal and final scope.
- Target repository and branch.
- Changed file summary.
- Commands executed and results.
- PR URL or blocker.
- Distillation candidate path or PR URL.
