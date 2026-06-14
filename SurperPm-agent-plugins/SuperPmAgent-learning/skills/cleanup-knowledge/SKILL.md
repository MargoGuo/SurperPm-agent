---
name: SuperPmAgent-cleanup-knowledge
description: Remove orphan data and fix inconsistencies in the knowledge repo. Cleans orphan discussion messages, stale execution logs, and validates INDEX.md references.
---

# Cleanup Knowledge

## When to trigger

Scheduled goal (weekly) or manually after major changes.

## Steps

1. **Orphan discussions**: Find messages in `.logs/discuss/messages/` for topic IDs that no longer exist in `topics.jsonl` → archive them
2. **Stale executions**: Executions with `status: running` older than 24h → mark as `failed` (crash recovery)
3. **Empty JSONL lines**: Remove blank lines from all `.jsonl` files
4. **INDEX consistency**: Check that `domain/*/INDEX.md` file references match actual files on disk → log mismatches
5. **Git sync**: Commit and push any cleanup changes

## Safety rules

- Never delete `.logs/` files — only fix contents
- Log every change for auditability
- Domain knowledge files are never auto-deleted (only flagged)

## Output

Summary of: orphan messages archived, stale executions fixed, INDEX mismatches found
