---
name: SuperPmAgent-distill-goals
description: Extract reusable learnings from completed goal executions. Reads execution logs and artifacts, identifies patterns/decisions/mistakes, writes Markdown files to learnings/ with memory-curve frontmatter.
---

# Distill Goals

## When to trigger

Scheduled goal (daily) or manually after a batch of goal executions complete.

## Inputs

- `KNOWLEDGE_REPO_PATH` env var → knowledge repo root
- `.logs/goal/meta/executions.jsonl` → completed executions with logs
- `.logs/goal/meta/goals.jsonl` → goal metadata

## Steps

1. Read all executions with `status: success` that haven't been distilled yet
2. For each execution, analyze:
   - What worked (patterns)
   - What failed first and how it was fixed (mistakes → lessons)
   - Key decisions made during execution
   - Reusable approaches
3. For each learning, create `learnings/<slug>.md` with frontmatter:
   ```yaml
   ---
   title: "Short learning title"
   category: pattern | mistake | decision | insight
   importance: 0.0-1.0
   confidence: 0.7
   created: YYYY-MM-DD
   tags: [tag1, tag2]
   pinned: false
   archived: false
   ---
   ```
4. Mark executions as distilled to avoid re-processing

## Output

- New files in `learnings/`
- Log of what was extracted

## Anti-patterns

- Don't extract trivial learnings ("installed packages")
- Don't duplicate existing learnings (check titles/tags first)
- Don't create more than 5 learnings per execution
