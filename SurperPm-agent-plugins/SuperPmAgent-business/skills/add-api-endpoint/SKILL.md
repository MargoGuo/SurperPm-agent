---
name: SuperPmAgent-add-api-endpoint
description: Apply when a requirement needs a new backend route, response field, or endpoint behavior that frontend code will consume.
argument-hint: "resource, method, route, request shape, response shape"
---

# Add API Endpoint

Use this pattern when a requirement changes backend contract or adds an endpoint.

## Clarify

- Who calls the endpoint?
- What request fields are required?
- What response shape is expected?
- What authentication or ownership rules apply?
- What failure cases should be visible to the PM or user?

## Likely Touchpoints

- Router or controller.
- Service or model query.
- Validation layer.
- API client helper.
- Frontend caller and tests.

## Flow

1. Use `repo-explorer` to find existing endpoint conventions.
2. Implement the smallest compatible route or response change.
3. Add tests for success and meaningful failure paths.
4. Verify frontend callers still match the response contract.
5. Submit a PR with explicit API contract notes.
