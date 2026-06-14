---
name: SuperPmAgent-add-filter
description: Apply when a requirement adds filtering, sorting, or search capability to an existing list or collection view.
argument-hint: "target list/collection, filter type (status/tag/search/sort), filter source (API param/frontend-only)"
---

# Add Filter / Sort / Search

Use this pattern for tasks such as adding tag filtering to article lists, status filtering (draft/published), search by keyword, or sort-by options.

## Clarify

- Which list or collection is being filtered?
- What is the filter criterion (status enum, tag, keyword, date range)?
- Is the filter applied server-side (API query param) or client-side (frontend-only)?
- Should the filter state persist in the URL (query params) or be ephemeral?
- Is there a default filter value?
- Does the filter need a UI control (dropdown, toggle, search input, tag chips)?

## Likely Touchpoints

- **Backend** (if server-side filtering):
  - Query parameter parsing in route/controller.
  - ORM query builder with filter condition.
  - Default value handling.
- **Frontend**:
  - Filter UI component (dropdown, input, toggle group).
  - API client call with filter parameters.
  - List component re-render on filter change.
  - URL query param sync (optional).
- **Tests**:
  - API test for filtered response (if server-side).
  - Component test for filter interaction.

## Flow

1. Use `repo-explorer` to find the target list's data flow (API → client → component).
2. Decide server-side vs client-side based on data volume and requirement.
3. If server-side: add query param support to the existing list endpoint.
4. Add filter UI control following existing form/input patterns.
5. Wire filter state to the API call or client-side filter function.
6. Handle edge cases: no results, clear filter, default state.
7. Run lint and relevant tests.

## Decision: Server-side vs Client-side

| Factor | Server-side | Client-side |
|---|---|---|
| Data volume | Large / paginated | Small / all loaded |
| Filter on DB field | Yes (status, tag FK) | No |
| Keyword search | Full-text needed | Simple string match OK |
| L1 frontend-only scope | Not allowed | Required |

## Anti-patterns

- Adding server-side filtering for an L1 frontend-only task.
- Fetching all data then filtering client-side on large collections.
- Forgetting to handle the "no results" state after filtering.
- Not providing a way to clear/reset the filter.
- Breaking existing list pagination when adding filters.
