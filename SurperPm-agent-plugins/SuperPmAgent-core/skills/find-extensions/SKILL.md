---
name: SuperPmAgent-find-extensions
description: Select extension prompts for a target skill, plugin, or MCP call. Use from pre-tool-use hooks or when a loop needs context-sensitive prompt additions.
argument-hint: "target plus task summary"
---

# Find Extensions

Pick only extension prompts that should affect the current action.

## Inputs

- `target`: for example `skill:coding`, `skill:run-tests`, `plugin:SuperPmAgent-core`, or `mcp:<name>`.
- `task_summary`: what the loop is trying to do now.
- `candidate_paths`: extension files under `knowledge/extensions/`.

## Selection Rules

1. Match exact target first.
2. Prefer high-priority extension frontmatter when the `when` text matches the current task.
3. Return no extension if none clearly applies.
4. Never inject all extensions by default.

## Output Format

```json
{
  "selected": [
    {
      "path": "knowledge/extensions/skills/coding/example.md",
      "reason": "Applies to frontend feature work with tests."
    }
  ]
}
```
