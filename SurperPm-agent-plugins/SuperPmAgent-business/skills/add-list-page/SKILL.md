---
name: SuperPmAgent-add-list-page
description: Apply when a requirement adds a new list/tab view for existing entities, such as adding a Drafts tab or a filtered article list.
argument-hint: "entity name, list context (tab/page/sidebar), filter criteria, display fields"
---

# Add List Page / Tab

Use this pattern for tasks such as adding a "Drafts" tab to a profile page, a "Popular Articles" sidebar, or a new filtered list view.

## Clarify

- Which entity does the list display?
- Where does the list appear (new page, new tab on existing page, sidebar)?
- What filter/sort criteria determine list membership?
- Which fields should each list item show?
- Is pagination needed? If so, what page size?
- Does the list need an empty state message?
- Is the data already available from an existing API, or does a new endpoint/query param need to be added?

## Likely Touchpoints

- **Backend** (only if new query/filter is needed):
  - Route or controller for the filtered query.
  - Query builder or ORM scope.
  - Existing list endpoint with new query parameter.
- **Frontend**:
  - Route or tab registration.
  - List component (reuse existing list item component when possible).
  - API client call with filter params.
  - Empty state component.
  - Navigation link or tab button.
- **Tests**:
  - API test for filtered response (if backend changed).
  - Component render test for the new list/tab.

## Flow

1. Use `repo-explorer` to find existing list pages and their component patterns.
2. Check if the needed data is already available from an existing API endpoint.
3. If backend changes are needed, add query parameter or route following existing conventions.
4. Create the list component by copying the nearest existing list pattern.
5. Register the route/tab in the navigation structure.
6. Add empty state handling.
7. Run existing lint/test commands.

## Cross-stack checklist

| Layer | Check |
|---|---|
| API | Does the endpoint return the right filtered set? |
| Client | Does the API client pass filter params correctly? |
| Component | Does the list item reuse the existing card/row component? |
| Navigation | Is the tab/link wired into the router or tab bar? |
| Empty state | Does "no items" show a meaningful message? |

## Anti-patterns

- Creating a completely new API endpoint when an existing one supports query params.
- Building a custom list item component when the existing one can be reused.
- Forgetting empty state handling.
- Adding backend filtering logic for a pure frontend filter (e.g., "show first 5 tags").
