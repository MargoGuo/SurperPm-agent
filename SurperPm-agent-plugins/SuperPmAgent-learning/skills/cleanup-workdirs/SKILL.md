---
name: SuperPmAgent-cleanup-workdirs
description: Remove stale goal execution workdirs under data/repos/. Cleans Claude session residuals (.claude.json, .last-cleanup, .claude/) and removes workdirs for completed goals older than 7 days.
---

# Cleanup Workdirs

## When to trigger

Scheduled goal (every 12 hours) or manually when disk space is low.

## Steps

1. Scan `data/repos/` for all goal workdirs
2. For each workdir, check:
   - Has `.claude.json` or `.last-cleanup` → remove these files
   - Goal status is `done` or `failed` AND last execution > 7 days ago → remove entire workdir
   - Empty workspace directories (no goal subdirs) → remove
3. Log what was cleaned and how much disk space was freed

## Safety rules

- Never remove workdirs for goals with status `doing` or `paused`
- Never remove workdirs for goals executed within the last 24 hours
- Keep workdirs for goals in `review` status (user may want to inspect)

## Output

Summary: `Cleaned N workdirs, freed X MB`
