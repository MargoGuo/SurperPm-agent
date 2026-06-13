---
name: SuperPmAgent-analyze-reference-material
description: Analyze fetched reference content or tables into clarify-ready candidate insights, evidence, and questions. Use when a normalized source already has `content_ref` or `table_ref` and the PM wants to learn from it without treating it as confirmed scope.
argument-hint: "source record plus content_ref or table_ref, PM request, and current clarify goal"
---

# Analyze Reference Material

Turn fetched reference material into a reviewable analysis artifact for
`/SuperPmAgent-core:clarify`.

## Use When

Use this skill when a normalized source already has `content_ref` or
`table_ref` and the PM wants to:

- reference this material;
- make something similar to it;
- analyze competitors;
- learn from this approach;
- extract possible requirements from the material.

## Inputs

- source record
- `content_ref` or `table_ref`
- PM raw request
- current `/clarify` goal

## Output

Write:

```text
attachments/sources/<slug>.analysis.md
```

## Source Record Update Rules

After writing `attachments/sources/<slug>.analysis.md`, update the original
source record when possible:

- set `analysis_ref = "attachments/sources/<slug>.analysis.md"`
- keep `content_ref` unchanged
- keep `table_ref` unchanged
- do not change `content_access`
- do not promote candidate requirements into `decisions.md`

`analysis_ref` is a pointer to derived evidence.
It is not PM-confirmed scope.

## Analysis Template

`analysis.md` should use this structure:

```md
# Reference Analysis

## Source Summary

Summarize what this source is about.

## Reference Object

Identify what product, page, feature, flow, campaign, or competitor this source describes.

## Feature Map

List observable features or modules.

## UX / Interaction Patterns

List user flows, page structures, interactions, or information hierarchy patterns.

## Differentiators

List notable highlights, differentiators, or competitive advantages.

## Candidate Requirements

List possible requirements that may be relevant to the current PM request.

Each candidate requirement should include:
- claim
- evidence
- confidence
- needs_pm_confirmation: true

## Not Confirmed Yet

List assumptions or source-derived points that PM has not confirmed.

## Clarify Questions

List targeted questions `/clarify` should ask PM next.

## Evidence

List source sections, headings, paragraphs, table rows, or cell ranges supporting the analysis.
```

## Rules

- Every candidate requirement should cite evidence from `content_ref` or
  `table_ref` when available.
- Candidate requirements are not confirmed decisions.
- PM confirmation is required before anything enters `decisions.md`.
- `/clarify` must ask the PM to confirm them before writing them to
  `decisions.md`.
- If evidence is weak, mark confidence low.
- Do not fabricate competitor features.
- Do not turn source analysis directly into implementation tasks.

## Clarify Handoff

This skill exists to improve the next clarification questions.

`/clarify` may use the resulting `analysis_ref` to:

- ask more targeted questions;
- surface likely requirement gaps;
- separate observed source behavior from PM-confirmed scope.

It must not:

- treat analysis as PM-confirmed requirement intent;
- skip PM confirmation just because the reference material is detailed.
