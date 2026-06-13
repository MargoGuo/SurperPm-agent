---
name: SuperPmAgent-repo-explorer
description: Locate relevant files, routes, models, components, tests, and commands in a Conduit fork before implementation. Use before code edits in a SuperPmAgent goal.
argument-hint: "goal plus target repository path"
---

# Repo Explorer

Find where to change code. Do not edit files.

## Inputs

- Goal and accepted scope.
- Target Conduit fork path.
- Session notes and decisions.
- Business skill hints, if any.

## Process

1. Identify 3-8 deterministic keywords from the goal.
2. Inspect repository structure and package scripts.
3. Locate candidate frontend, backend, model, route, and test files.
4. Trace data flow from UI to API to persistence when the task is cross-stack.
5. Record unknowns and risks.

## Output

```text
Goal Snapshot:
Keywords:
Candidate Files:
Data Flow:
Implementation Hints:
Verification Plan:
Risks:
```

Prefer local repository search and CLI tools. Avoid external MCP tools for code exploration unless the team explicitly changes this rule.
