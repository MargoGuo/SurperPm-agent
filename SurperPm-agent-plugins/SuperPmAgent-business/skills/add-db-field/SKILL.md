---
name: SuperPmAgent-add-db-field
description: Apply when a requirement adds a persistent field to an existing model and needs cross-stack consistency.
argument-hint: "entity name, field name, field type, UI/API expectations"
---

# Add Database Field

Use this pattern for tasks such as adding `coverImage` to `Article` or `likeCount` to `Comment`.

## Clarify

- Which entity owns the field?
- Is the field required or optional?
- What is the default value for existing records?
- Should the field be writable, readable, or both?
- Which UI surfaces must display or edit it?

## Likely Touchpoints

- Model or migration definition.
- Validation and serialization.
- Create and update endpoints.
- API response consumers.
- Forms, cards, detail pages, and tests.

## Flow

1. Use `repo-explorer` to trace the entity from persistence to UI.
2. Use `coding` to update backend and frontend consistently.
3. Use `run-tests` for backend and frontend checks.
4. Use `debugger` if cross-stack contracts fail.
5. Use `submit-pr` after verification.

## Distill After Success

Capture entity-specific file paths, migration conventions, and tests that proved the contract.
