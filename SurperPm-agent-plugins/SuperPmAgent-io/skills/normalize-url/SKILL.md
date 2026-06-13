---
name: SuperPmAgent-normalize-url
description: Normalize URL-like PM inputs into a reviewable source record before `/SuperPmAgent-core:clarify` updates session files. Use as the generic fallback for unknown or non-specialized URLs.
argument-hint: "session name plus source URL and any user-supplied context"
---

# Normalize URL

Turn a raw external link into a normalized session input record.

This skill is a preprocessing step for `/SuperPmAgent-core:clarify`.
It does not replace clarification and it does not write executable intent into
`notes.md` by itself.

## Use When

Use this skill when the PM provides:

- a generic webpage URL;
- an issue URL;
- an unknown URL that does not clearly match a specialized input skill;
- a link-like reference that still needs `/clarify` to confirm what matters.

Prefer specialized routing when the URL is clearly:

- a Feishu document -> use `normalize-feishu-doc`
- a Feishu sheet, table, or bitable link -> use `normalize-feishu-sheet`
- a Bilibili video -> use `normalize-bilibili-video`
- a Douyin video -> use `normalize-douyin-video`

## Inputs

- `session_name`
- `source_url`
- `raw_request` or surrounding PM message
- Optional user-supplied title or summary

## Output Goal

Produce a normalized source record that follows
the session I/O protocol document in this repo.

## Required Record Shape

```json
{
  "record_type": "normalized_input",
  "source_type": "url",
  "source_uri": "https://example.com/item",
  "title": "Short human-readable label",
  "summary": "Short extracted or user-supplied summary",
  "raw_request": "Original PM wording, if any",
  "user_context": "What the PM said they want to reference from this source",
  "content_access": "link_only",
  "capture_method": "link-plus-user-context",
  "content_ref": null,
  "table_ref": null,
  "analysis_ref": null,
  "evidence_policy": "External source is supporting context only; PM confirmation is required before it becomes a decision.",
  "extracted_points": [
    "Point one",
    "Point two"
  ],
  "risks": [
    "Potential uncertainty or extraction caveat"
  ],
  "provider_metadata": {
    "provider": "unknown",
    "capture_method": "link-plus-user-context",
    "content_access": "link_only",
    "needs_followup_confirmation": true
  }
}
```

Allowed values:

- `content_access`: `link_only`, `pm_summary`, `fetched_text`, `fetched_table`, `partial_fetch`
- `capture_method`: `link_only`, `link-plus-user-context`, `link-plus-summary`, `fetched_text`, `lark-doc`, `lark-sheet`
- `provider_metadata.capture_method`: `link_only`, `link-plus-user-context`, `link-plus-summary`, `fetched_text`, `lark-doc`, `lark-sheet`
- `provider_metadata.content_access`: `link_only`, `pm_summary`, `fetched_text`, `fetched_table`, `partial_fetch`

## Write Path

Write the normalized record under:

```text
<KNOWLEDGE_REPO_PATH>/sessions/<session-name>/attachments/sources/<slug>.json
```

Where `<slug>` should be a short stable name derived from the URL host and page
purpose when possible.

## Session Update Rules

When using this skill:

1. Write or update the normalized source record in `attachments/sources/`.
2. Add a short note to `conversation.md` that the source was attached or
   referenced.
3. Do not dump the raw webpage or raw link into `notes.md`.
4. Reflect only stable clarified meaning into `notes.md`.
5. Record only PM-confirmed boundaries in `decisions.md`.

## Classification Guidance

- Use `source_type: "url"` for generic links.
- If the link is clearly a Feishu doc, route to `normalize-feishu-doc`
  instead of this fallback.
- If the link is clearly a Feishu sheet, table, or bitable, route to
  `normalize-feishu-sheet` instead of this fallback.
- If the link is clearly a Bilibili video, route to
  `normalize-bilibili-video` instead of this fallback.
- If the link is clearly a Douyin video, route to
  `normalize-douyin-video` instead of this fallback.

## MVP Limits

For the first implementation wave, this skill should:

- prefer link registration over deep crawling;
- prefer user-supplied summaries over speculative extraction;
- keep records small and reviewable;
- surface uncertainty in `risks`.

It should not:

- invent scope from an uninspected link;
- mark a session `ready_for_goal: yes` from a link alone;
- let a raw link enter `notes.md` without `/clarify` confirming the actual
  requirement meaning;
- replace clarification questions when ambiguity remains.
