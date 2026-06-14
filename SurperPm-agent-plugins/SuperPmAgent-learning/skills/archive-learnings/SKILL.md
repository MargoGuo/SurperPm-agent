---
name: SuperPmAgent-archive-learnings
description: Batch-archive learnings that have decayed below the retention threshold. Uses memory-curve scoring (importance × e^(-λt) + access_bonus) to identify expired entries.
---

# Archive Learnings

## When to trigger

Scheduled goal (weekly) or as part of Knowledge Maintenance.

## Steps

1. Read all `learnings/*.md` files
2. Compute memory-curve score for each: `score = importance × e^(-λt) + 0.5 × ln(1 + access_count)`
3. For learnings with `score < 0.1` AND `pinned: false`:
   - Set `archived: true` in frontmatter
4. For learnings with `score < 0.01`:
   - Move to `learnings/archive/` directory
5. Log all archived learnings with their final scores

## Decay rates (λ by category)

- decision: 0.010 (slow decay — decisions persist)
- pattern: 0.020
- insight: 0.030
- mistake: 0.050 (fast decay — lessons learned, move on)
- external: 0.040

## Safety rules

- Never archive pinned learnings
- Never delete — only move to archive/
- Log every archival with reason and score
