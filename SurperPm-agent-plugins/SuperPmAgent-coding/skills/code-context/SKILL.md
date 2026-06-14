---
name: code-context
description: |
  Optional deep locate for large or multi-module repos via local CLI (no MCP).
  Wraps analyze (keyword scan) and explore (expand/search/trace). Read-only.
---

# code-context

Use when `repo-explorer` needs compressed context in a large repo, or when grep alone is too noisy.

## CLI location

From the target repo (or any cwd), run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/tools/code_context.py" analyze \
  --project "<REPO_ROOT>" \
  --keywords "Article,coverImage,Comment" \
  --focus "src"

python "${CLAUDE_PLUGIN_ROOT}/tools/code_context.py" explore \
  --project "<REPO_ROOT>" \
  --mode expand \
  --query "src/components/Article.tsx:10-120"

python "${CLAUDE_PLUGIN_ROOT}/tools/code_context.py" explore \
  --project "<REPO_ROOT>" \
  --mode search \
  --query "readingCount"

python "${CLAUDE_PLUGIN_ROOT}/tools/code_context.py" explore \
  --project "<REPO_ROOT>" \
  --mode trace \
  --query "createArticle" \
  --max-depth 3
```

If `CLAUDE_PLUGIN_ROOT` is unavailable, resolve the path to `SuperPmAgent-coding/tools/code_context.py` in the installed plugin.

## When to use

- Monorepo or >50 likely source files for the goal.
- Cross-stack field propagation (UI → API → model).
- Need import/call hints before reading full files.

Skip for tiny L1 frontend-only tasks where manifest + 2-3 grep hits suffice.

## Steps

1. Derive 3-8 keywords from the goal (entities, routes, field names).
2. Run `analyze` with optional `--focus` on the likely app subdirectory.
3. Pick top 3-5 candidate paths from JSON output.
4. Run `explore --mode expand` on the highest-value ranges.
5. Use `search` or `trace` only when data flow is still unclear.
6. Pass summarized paths and snippets to `repo-explorer` output — do not edit code here.

## Output

Append to the repo-explorer locate report:

```markdown
## Code Context (CLI)

Keywords:

Top CLI Candidates:
| Path | Why | Snippet / line refs |
|---|---|---|

Trace / expand notes:
```

## Anti-patterns

- Requiring MCP or `.mcp.json` configuration.
- Running analyze without keywords (too broad).
- Treating CLI output as proof of correctness without reading target files.
- Editing files from this skill.
