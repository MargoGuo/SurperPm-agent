---
name: SuperPmAgent-add-ui-form
description: Apply when a requirement adds or changes user input in an existing frontend form.
argument-hint: "form name, field name, validation, submit behavior"
---

# Add UI Form

Use this pattern for requirements that add visible user input, such as a URL field in an article editor.

## Clarify

- Which form changes?
- What label, placeholder, and validation should users see?
- Is the field required?
- What API request field should receive the value?
- What should happen on validation or save failure?

## Likely Touchpoints

- Form component.
- Local form state.
- API request mapping.
- Display surface after save.
- Component or integration tests.

## Flow

1. Use `repo-explorer` to find the form, API caller, and display surface.
2. Implement the input and state mapping.
3. Keep UI copy consistent with existing project style.
4. Run frontend checks and any API contract tests needed.
5. Submit a PR with screenshots or manual verification notes when UI changed.
