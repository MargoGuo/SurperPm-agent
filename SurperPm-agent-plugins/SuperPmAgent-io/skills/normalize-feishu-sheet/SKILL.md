---
name: SuperPmAgent-normalize-feishu-sheet
description: Normalize a Feishu/Lark sheet, table, or bitable link into a content-aware session source record before `/SuperPmAgent-core:clarify` updates IntentSpec files. Use for competitor matrices, feature lists, pricing tables, and similar table-shaped PM inputs.
argument-hint: "session name plus Feishu sheet or bitable URL and any PM context"
---

# Normalize Feishu Sheet

Turn a Feishu/Lark sheet, table, or bitable link into a normalized session
input record.

## Use When

Use this skill when:

- the PM provides a Feishu Sheet or Lark Sheet link;
- the PM provides a Feishu Base or Bitable link that behaves like a table;
- the PM says the table is a competitor matrix, feature list, pricing table,
  user feedback table, or requirement priority table.

## Inputs

- `session_name`
- `feishu_sheet_url`
- `raw_request` or surrounding PM message
- Optional user-supplied title or summary
- Optional current `/clarify` goal or reference angle

## Provider Strategy

This skill should support three levels of normalization maturity.

### Level 0: link-only

- Cannot read the sheet.
- Register the source record only.
- Ask the PM to paste a table summary or grant access.

### Level 1: fetched-table

- Sheet content is readable through an available Feishu/Lark skill, MCP, or
  tool.
- Preserve a table snapshot as markdown.
- Set `content_access = fetched_table`.
- Write `table_ref`.

### Level 2: analyzed-reference

- Analyze table content after it is fetched.
- Extract competitors, feature columns, common features, differentiators,
  candidate requirements, and clarification questions.
- Write `analysis_ref`.

## Write Paths

Write under the session source attachment directory:

```text
attachments/sources/<slug>.json
attachments/sources/<slug>.table.md
attachments/sources/<slug>.analysis.md
```

Only set `analysis_ref` when `attachments/sources/<slug>.analysis.md` has
actually been written.
If fetched content or table exists but analysis has not been produced yet, set
`analysis_ref = null`.

## Record Shape

```json
{
  "record_type": "normalized_input",
  "source_type": "feishu_sheet",
  "source_uri": "https://example.feishu.cn/sheets/xxxxx",
  "title": "optional",
  "summary": "Short extracted or user-supplied summary",
  "raw_request": "PM original utterance",
  "user_context": "What PM wants to reference",
  "content_access": "fetched_table",
  "capture_method": "lark-sheet",
  "content_ref": null,
  "table_ref": "attachments/sources/<slug>.table.md",
  "analysis_ref": "attachments/sources/<slug>.analysis.md",
  "evidence_policy": "External source is supporting context only; PM confirmation is required before it becomes a decision.",
  "extracted_points": [],
  "risks": [],
  "provider_metadata": {
    "provider": "feishu",
    "tool": "lark-sheet",
    "content_access": "fetched_table",
    "sheet_names": [],
    "range": "optional",
    "needs_followup_confirmation": true
  }
}
```

Link-only example:

```json
{
  "record_type": "normalized_input",
  "source_type": "feishu_sheet",
  "source_uri": "https://example.feishu.cn/sheets/xxxxx",
  "title": null,
  "summary": null,
  "raw_request": "PM original utterance",
  "user_context": "What PM wants to reference",
  "content_access": "link_only",
  "capture_method": "link-plus-user-context",
  "content_ref": null,
  "table_ref": null,
  "analysis_ref": null,
  "evidence_policy": "External source is supporting context only; PM confirmation is required before it becomes a decision.",
  "extracted_points": [],
  "risks": [
    "Feishu sheet content was not readable; PM must provide summary, export, or grant access."
  ],
  "provider_metadata": {
    "provider": "feishu",
    "tool": null,
    "content_access": "link_only",
    "sheet_names": [],
    "range": null,
    "needs_followup_confirmation": true
  }
}
```

## Table Snapshot Rules

- preserve sheet name if known;
- preserve the header row;
- preserve visible rows used for analysis;
- if the range is too large, summarize and record omitted rows;
- do not invent missing cells;
- do not infer hidden columns unless explicitly present;
- preserve row or column references when possible.

## Reference Analysis Rules

Look for:

- competitor names;
- feature columns;
- common features;
- differentiating features;
- pricing, plan, or status if present;
- candidate requirements;
- clarification questions.

Table-derived insights are candidate insights, not confirmed requirements.
`/clarify` must ask the PM to confirm them before promoting them into
`decisions.md`.

## Fallback Rules

If the sheet cannot be read:

1. Still register the source as `feishu_sheet`.
2. Preserve the original link in `source_uri`.
3. Set:
   - `content_access = link_only`
   - `capture_method = link-plus-user-context`
   - `content_ref = null`
   - `table_ref = null`
   - `analysis_ref = null`
4. Add a risk such as:
   - `Feishu sheet content was not readable during normalization`
   - `Table access may require additional auth or permission`
5. Ask the PM for a summary, screenshot context, key rows, or exported subset.

## MVP Limits

For the first implementation wave, this skill should:

- define the record contract for Feishu table-shaped inputs;
- preserve a markdown table snapshot when readable;
- support later reference analysis handoff.

It should not:

- pretend hidden or inaccessible rows were read;
- convert table insights directly into confirmed PM decisions;
- implement custom Feishu API logic inside SuperPmAgent backend code.

## Example

Typical usage:

- PM says: "Use this Feishu sheet as the competitor matrix."
- This skill registers the source.
- If readable, it writes `table_ref`.
- If the table matters for requirement clarification, `/clarify` can hand the
  fetched table to `analyze-reference-material`.
