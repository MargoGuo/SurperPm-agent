---
name: SuperPmAgent-sync-knowledge
description: Force bidirectional knowledge repo sync — commit local changes, pull remote updates, push back. Handles merge conflicts by creating resolution goals.
---

# Sync Knowledge

## When to trigger

Part of Knowledge Maintenance goal, or manually when sync issues are detected.

## Steps

1. Check for local uncommitted changes in `KNOWLEDGE_REPO_PATH`
2. If dirty: `git add -A` + `git commit -m "auto-sync: YYYY-MM-DD HH:MM"`
3. `git pull --rebase origin main`
4. If rebase conflict:
   - `git rebase --abort`
   - `git merge origin/main --strategy-option=theirs`
   - Log conflicted files
5. `git push origin main`
6. Reload KnowledgeStore cache

## Safety rules

- On conflict, prefer remote version (--strategy-option=theirs) to avoid data loss
- Always commit before pull to preserve local state
- Retry once if "unstaged changes" error (race with running backend)
