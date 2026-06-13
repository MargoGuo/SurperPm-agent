---
name: SuperPmAgent-find
description: Discover SuperPmAgent skills and knowledge by convention before planning or coding a goal. Use whenever a delivery loop needs relevant plugin, business, or knowledge context.
argument-hint: "natural language query"
---

# Find

Discover relevant SuperPmAgent resources without a central registry.

## Search Roots

Scan these paths from the marketplace root:

- `SuperPmAgent-*/skills/INDEX.md`
- `knowledge/**/INDEX.md`
- `knowledge/extensions/INDEX.md`

## Process

1. Restate the query in one sentence.
2. Search skill indexes for matching capabilities.
3. Search knowledge indexes for matching domain, profile, session, or convention context.
4. Return candidate paths with a short reason for each.
5. Prefer narrow candidates over broad context dumps.

## Output Format

```text
Query:
Candidates:
- path:
  type: skill | knowledge | extension
  reason:
  confidence: high | medium | low
Next:
```

Do not edit files. This skill only locates context.
