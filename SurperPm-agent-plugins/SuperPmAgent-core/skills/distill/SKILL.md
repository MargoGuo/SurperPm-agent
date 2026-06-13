---
name: SuperPmAgent-distill
description: Convert a completed SuperPmAgent loop into reusable skill, knowledge, or extension candidates and prepare a PR back to the marketplace.
argument-hint: "loop summary path or run id"
---

# Distill

Distill reusable learning after a loop completes.

## Inputs

- Goal and final scope.
- Conversation or session files.
- Changed files and diff summary.
- Test commands and results.
- Failures and fixes.
- PR URL or blocker.

## Routing Decision

Choose one destination:

- `SuperPmAgent-coding/skills/fixes/`: reusable engineering fix or tool workaround.
- `SuperPmAgent-business/skills/`: reusable business-change pattern.
- `knowledge/domain/`: domain convention or Conduit fact.
- `knowledge/extensions/`: context-sensitive prompt rule.

## Rules

- Do not overwrite existing knowledge silently.
- Keep a candidate small and reviewable.
- Include source evidence from the run.
- Open or prepare a PR rather than directly promoting unreviewed knowledge.

## Output

Return:

- Proposed destination.
- Candidate file path.
- Why it is reusable.
- Evidence from the loop.
- Review notes for humans.
