---
name: SuperPmAgent-add-detail-page
description: Apply when a requirement adds a new detail view, info section, or expanded display for an existing entity.
argument-hint: "entity name, display context (page section/modal/tab), fields to show, computed fields"
---

# Add Detail Page / Section

Use this pattern for tasks such as adding a word count display to article detail, an "About Me" tab to profile, or a reading time estimate section.

## Clarify

- Which entity's detail view is being extended?
- Is this a new section on an existing page, a new tab, or a standalone page?
- Which fields should be displayed? Are any computed (e.g., word count, time ago)?
- Does the computation happen frontend-only or does it need backend support?
- Are there formatting requirements (e.g., "X minutes ago", "1,234 words")?
- Should the section be visible to all users or only the entity owner?

## Likely Touchpoints

- **Backend** (only if new data or computation is needed):
  - Model field or virtual/computed property.
  - Serializer to include the new field in API response.
- **Frontend**:
  - Detail page component modification or new sub-component.
  - Data formatting utility (date formatting, number formatting).
  - Conditional rendering based on data availability or user role.
- **Tests**:
  - Unit test for computed values (if frontend-computed).
  - Component render test for the new section.

## Flow

1. Use `repo-explorer` to find the existing detail page component and its data flow.
2. Determine if the data is already available in the API response.
3. If frontend-computed: add utility function and display component.
4. If backend-needed: add field to serializer/response, then consume in frontend.
5. Follow existing detail page layout patterns for styling and placement.
6. Run lint and relevant tests.

## Scope guard

- L1 tasks (frontend-only) must compute values from existing API data — do not
  add backend fields or API changes for an L1.
- If the requirement says "front-end fake data", use static/computed values and
  do not modify the backend.

## Anti-patterns

- Adding a backend field when the value can be computed from existing frontend data.
- Breaking the existing detail page layout by inserting elements without following conventions.
- Forgetting to handle missing/null data (e.g., article with empty body → word count = 0).
