# Plugin Index

Authoritative skill/command index for the `find` skill. Keep in sync with the
actual `SuperPmAgent-*/skills/` folders and `SuperPmAgent-*/commands/`.

## Core (`SuperPmAgent-core`)

- `commands/goal` - Goal entry and delivery orchestration
- `commands/clarify` - Clarify a PM request into a session IntentSpec
- `commands/distill` - Manual distill modes (`summary`, `dream`)
- `skills/find` - Resource discovery (skills / domain / learnings / profiles / extensions)
- `skills/find-extensions` - Extension prompt discovery (hook-invoked)
- `skills/distill` - Post-loop knowledge distillation into `knowledge/domain/`
- `hooks/` - `pre-tool-use.py`, `stop.py`

## IO (`SuperPmAgent-io`)

- `skills/normalize-url` - Generic URL normalization fallback
- `skills/normalize-feishu-doc` - Feishu/Lark document normalization
- `skills/normalize-feishu-sheet` - Feishu/Lark sheet/bitable normalization
- `skills/normalize-bilibili-video` - Bilibili video reference normalization
- `skills/normalize-douyin-video` - Douyin video reference normalization
- `skills/analyze-reference-material` - Turn fetched references into clarify-ready insights
- `skills/export-feishu-prd` - Feishu PRD artifact registration
- `skills/export-ppt` - PPT artifact registration
- `contracts/IO-PROTOCOL.md` - Session input/output protocol

## Coding (`SuperPmAgent-coding`)

- `skills/repo-explorer` - Read-only repository exploration and locate report
- `skills/coding` - Focused implementation after locate evidence
- `skills/run-tests` - Test/lint/build selection and failure capture
- `skills/debugger` - Bounded root-cause investigation
- `skills/acceptance-review` - Final acceptance/scope gate before PR
- `skills/submit-pr` - Branch, commit, and PR submission
- `skills/code-context` - Optional deep locate via local CLI (no MCP)
- `skills/fixes/` - Distilled CI-failure self-heal patterns (auto-grow)
- `tools/code_context.py` - Local code-context CLI

## Business (`SuperPmAgent-business`)

- `skills/add-db-field` - Persistent field with cross-stack propagation
- `skills/add-api-endpoint` - New backend route / response contract
- `skills/add-ui-form` - New or changed user input in an existing form
- `skills/gen-feishu-design` - Feishu requirements → design + task artifacts
