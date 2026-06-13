---
name: SuperPmAgent-export-ppt
description: Export a clarified session into a PPT-oriented artifact record and register the derived output back into the session. Use when a PM wants a slide outline, report deck plan, or presentation metadata derived from clarified session files.
argument-hint: "session name plus optional title or destination details"
---

# Export PPT

Turn a clarified SuperPmAgent session into a PPT-oriented artifact record.

This skill is a post-clarification delivery step. It does not replace the
session. It produces a derived presentation artifact description and records
that output back into the same session.

## Use When

Use this skill when the PM asks to:

- generate a PPT
- output presentation material
- make a slide deck
- organize the requirement into slides

## Inputs

- `session_name`
- Optional title override
- Optional destination details
- Optional export intent, such as status report, requirement review, or kickoff

## Source Of Truth

Read from the session in this order:

1. `notes.md` is the primary source of truth
2. `decisions.md` is the confirmed-boundary source of truth
3. `conversation.md` is supporting context only
4. PPT is a derived artifact and cannot replace `notes.md`
5. `/goal` should consume the session, not the PPT artifact

## Output Goal

Produce and register a normalized output record that follows the session I/O
protocol and preserves auditability of which session files drove the export.

## Required Output Record

```json
{
  "record_type": "derived_output",
  "output_type": "ppt",
  "title": "需求汇报 PPT",
  "artifact_uri": "session-export://ppt/requirement-review",
  "source_session": "<KNOWLEDGE_REPO_PATH>/sessions/add-phone-field-20260613",
  "source_files": [
    "notes.md",
    "decisions.md"
  ],
  "summary": "Slide outline and export metadata for requirement review.",
  "slides_outline": [
    "Background and problem",
    "User goals",
    "Scope and key features"
  ],
  "risks": [
    "Binary .pptx generation is not part of the MVP export path."
  ],
  "provider_metadata": {
    "provider": "SuperPmAgent-session-export",
    "artifact_kind": "ppt-outline",
    "binary_generated": false
  },
  "generated_at": "2026-06-13Z"
}
```

## Write Path

Write the artifact metadata record under:

```text
<KNOWLEDGE_REPO_PATH>/sessions/<session-name>/attachments/exports/<slug>.json
```

Where `<slug>` should be a short stable label such as `ppt-outline` or
`requirement-review-ppt`.

## Session Update Rules

When using this skill:

1. Keep `notes.md` as the executable IntentSpec for `/goal`.
2. Keep `decisions.md` as the PM-confirmed boundary record.
3. Treat `conversation.md` only as supporting context for framing.
4. Register the export artifact in `attachments/exports/`.
5. Do not replace `notes.md` with slide text or artifact links.
6. Do not let the PPT artifact become the new source of truth.
7. If the export process introduces a new PM-confirmed presentation decision,
   record that in `decisions.md`; otherwise keep the export metadata separate.

## Suggested PPT Structure

Suggested structure for the MVP slide plan:

1. 背景与问题
2. 用户目标
3. 需求范围
4. 核心功能
5. 非目标 / Out of Scope
6. 验收标准
7. 风险与待确认事项
8. 下一步

## MVP Limits

For the MVP, this skill may generate only:

- PPT outline
- slide plan
- artifact metadata

It does not require a real binary `.pptx` file.

If a real `.pptx` is needed, the skill must record that dependency in
`provider_metadata` or `risks`, for example by noting that binary deck
generation depends on external tooling not covered by this MVP.

This skill must not:

- treat the PPT as a replacement for `notes.md`;
- make `/goal` consume the PPT instead of the session;
- present unresolved conversation fragments as confirmed requirements.

## Example

PM says:

`帮我把这个 session 生成一份 PPT 汇报。`

Skill should:

1. Read `notes.md` first and `decisions.md` second.
2. Build a slide outline from stable clarified session content.
3. Register a `ppt` export record under `attachments/exports/`.
4. Mark the artifact as derived output.
5. Keep `/goal` pointed at the session rather than the PPT.
