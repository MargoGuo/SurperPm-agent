---
name: SuperPmAgent-normalize-feishu-doc
description: Normalize a Feishu/Lark document link into a content-aware session source record before `/SuperPmAgent-core:clarify` updates IntentSpec files. Use when the PM provides a Feishu document as formal requirement or reference material.
argument-hint: "session name plus Feishu document URL and any PM context"
---

# Normalize Feishu Doc

Turn a Feishu/Lark document link into a normalized session input record.

This skill specializes the generic URL normalization path for Feishu document
inputs. It should be preferred over `normalize-url` when the source is clearly
a Feishu doc and the document is meant to inform requirement clarification.

See [`TESTING.md`](TESTING.md) for the manual MVP verification flow.

## Use When

Use this skill when:

- the PM provides a Feishu/Lark document link;
- the document may be referenced directly or through shared browser context;
- the document is part of the requirement input, not just a casual reference;
- the team wants a stable session record that preserves where requirement
  context came from.

## Inputs

- `session_name`
- `feishu_doc_url`
- `raw_request` or surrounding PM message
- Optional user-supplied title or summary
- Optional current `/clarify` goal or reference angle

## Provider Strategy

This skill should support three levels of normalization maturity.

### Level 0: link-only

- No readable content is available.
- Only register the source record.
- Set `content_access = link_only`.
- Ask the PM to provide a summary or grant access.

### Level 1: fetched-text

- Feishu/Lark doc content is readable through an available skill, MCP, or
  tool.
- Preserve a content snapshot as markdown.
- Set `content_access = fetched_text`.
- Write `content_ref`.

### Level 2: analyzed-reference

- After content is fetched, run reference analysis.
- Extract product or competitor insights, candidate requirements, and targeted
  clarification questions.
- Write `analysis_ref`.

## Tool / Skill Handoff

If available, prefer an existing Feishu/Lark document skill or MCP tool such
as `lark-doc`, `lark-cli`, or a Feishu MCP server.

Rules:

- Prefer existing Feishu/Lark document capabilities over inventing a parallel
  fetch path.
- Do not implement Feishu API logic inside SuperPmAgent backend code.
- Do not fabricate document content when fetch fails.
- If content fetch succeeds, preserve a small reviewable subset rather than
  dumping the whole document blindly.

## Write Paths

Write under the session source attachment directory:

```text
attachments/sources/<slug>.json
attachments/sources/<slug>.content.md
attachments/sources/<slug>.analysis.md
```

Rules:

- If content cannot be read:
  - write only the JSON record;
  - set `content_ref = null`;
  - set `analysis_ref = null`;
  - set `content_access = link_only`;
  - explain the fetch or permission limit in `risks`.
- If content fetch succeeds:
  - write the JSON record;
  - write `content.md`;
  - attempt to write `analysis.md`;
  - set `content_access = fetched_text`.
- Only set `analysis_ref` when `attachments/sources/<slug>.analysis.md` has
  actually been written.
- If fetched content exists but analysis has not been produced yet, set
  `analysis_ref = null`.

## Required Record Shape

Fetched-text example:

```json
{
  "record_type": "normalized_input",
  "source_type": "feishu_doc",
  "source_uri": "https://example.feishu.cn/docx/xxxxx",
  "title": "optional",
  "summary": "Short extracted or user-supplied summary",
  "raw_request": "PM original utterance",
  "user_context": "What PM wants to reference",
  "content_access": "fetched_text",
  "capture_method": "lark-doc",
  "content_ref": "attachments/sources/<slug>.content.md",
  "table_ref": null,
  "analysis_ref": "attachments/sources/<slug>.analysis.md",
  "evidence_policy": "External source is supporting context only; PM confirmation is required before it becomes a decision.",
  "extracted_points": [],
  "risks": [],
  "provider_metadata": {
    "provider": "feishu",
    "tool": "lark-doc",
    "content_access": "fetched_text",
    "needs_followup_confirmation": true
  }
}
```

Link-only example:

```json
{
  "record_type": "normalized_input",
  "source_type": "feishu_doc",
  "source_uri": "https://example.feishu.cn/docx/xxxxx",
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
    "Feishu document content was not readable; PM must provide summary or grant access."
  ],
  "provider_metadata": {
    "provider": "feishu",
    "tool": null,
    "content_access": "link_only",
    "needs_followup_confirmation": true
  }
}
```

## Content Snapshot Rules

When content is readable:

- preserve the source title if known;
- store a markdown snapshot that is reviewable in Git;
- keep section headings when possible;
- keep only the content range needed for current clarification if the source is
  large;
- record truncation or omission in `risks` when only part of the content is
  preserved;
- never invent missing sections.

## Evidence Rules

- `extracted_points` must cite document section, heading, or paragraph when
  possible.
- Do not promote extracted points into `decisions.md` unless the PM confirms
  them.
- `notes.md` may mention them as candidate insights or open questions, not as
  confirmed facts.
- `analysis_ref` is a derived analysis artifact, not a source of truth.
- PM-confirmed decisions still belong in `decisions.md`.

## Session Update Rules

When using this skill:

1. Write or update the normalized source record in `attachments/sources/`.
2. Add a short source-registration note to `conversation.md`.
3. Do not copy the full document into `notes.md`.
4. Reflect only clarified stable meaning into `notes.md`.
5. Record only PM-confirmed boundaries in `decisions.md`.
6. Do not treat Feishu document content as automatically PM-confirmed.

## Fallback Rules

If the document cannot be read because of auth, permission, or fetch limits:

1. Still register the source as `feishu_doc`.
2. Preserve the original link in `source_uri`.
3. Use any PM-supplied description as context, not as fetched fact.
4. Preserve the PM's stated reference angle in `user_context`.
5. Set:
   - `capture_method = link-plus-user-context`
   - `content_access = link_only`
   - `content_ref = null`
   - `table_ref = null`
   - `analysis_ref = null`
6. Add a risk such as:
   - `Feishu content could not be fetched during normalization`
   - `Document access may require additional auth or permission`
7. Continue clarification, but ask the PM for summary, access, or the relevant
   section before using the source as strong evidence.

## MVP Limits

For the first implementation wave, this skill should:

- treat the Feishu doc as a structured source type;
- support link-only registration plus fetched-text normalization guidance;
- preserve content and analysis as small markdown artifacts;
- reuse existing Feishu or Lark capabilities for reads rather than building a
  new fetch path.

It should not:

- assume the full document content is final or PM-approved;
- treat the document alone as sufficient for `ready_for_goal: yes`;
- let unconfirmed Feishu text bypass `/clarify` and land directly as a
  decision;
- replace focused clarification questions when requirement ambiguity remains.
