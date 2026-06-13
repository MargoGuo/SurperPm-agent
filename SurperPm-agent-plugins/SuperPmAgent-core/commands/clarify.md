---
description: Clarify an ambiguous PM request into an executable SuperPmAgent session.
argument-hint: "[raw PM request]"
allowed-tools: Read, Write, Edit, Glob
---

# SuperPmAgent Clarify

Turn a raw PM request into a session that a delivery loop can execute.

## Clarification Goals

Ask for:

- User-facing objective.
- Concrete scope.
- Out of scope.
- Acceptance criteria.
- Data or UI edge cases.
- Required verification.

Avoid asking for implementation details that the AI engineering loop can infer from the repository.

## Output

Write or update a session folder under `knowledge/sessions/<session-name>/`:

- `conversation.md`: questions and answers.
- `notes.md`: facts, constraints, and assumptions.
- `decisions.md`: accepted scope, rejected scope, and test expectations.

If the request is already clear, write the session directly and do not over-question the PM.
