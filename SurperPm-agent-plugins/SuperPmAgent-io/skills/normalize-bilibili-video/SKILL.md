---
name: SuperPmAgent-normalize-bilibili-video
description: Normalize a Bilibili video link into a reviewable session source record before `/SuperPmAgent-core:clarify` updates IntentSpec files. Use when a PM references a Bilibili video in shared browser discussion and the team needs a stable source record without pretending the full video was understood.
argument-hint: "session name plus Bilibili URL and any PM context"
---

# Normalize Bilibili Video

Turn a Bilibili video link into a normalized session input record.

This skill specializes the generic URL normalization path for shared browser
video references. It supports the MVP `shared browser context /
link-plus-user-context` model: register the link, preserve what the PM said
they want to reference, surface uncertainty, and let `/clarify` ask for the
actual requirement-bearing parts.

## Use When

Use this skill when the PM input or active session includes:

- `bilibili.com`
- `b23.tv`
- `Bilibili video`
- `bilibili reference in shared browser`
- a Bilibili video opened in the shared browser

and the PM is trying to reference that video during requirement discussion.

## Inputs

- `session_name`
- `bilibili_video_url`
- `raw_request` or surrounding PM message
- Optional PM-provided `title`
- Optional PM-provided `summary`
- Optional PM-provided `user_context` describing which parts matter

## Output Goal

Produce a normalized source record that follows the session I/O protocol and
keeps the external video as supporting context, not executable requirement
truth.

## Required Record Shape

```json
{
  "record_type": "normalized_input",
  "source_type": "bilibili_video",
  "source_uri": "https://www.bilibili.com/video/BVxxxx",
  "title": "Optional title if known",
  "summary": "Optional summary if available or PM-provided",
  "raw_request": "PM's original utterance",
  "user_context": "What PM said they want to reference from this source",
  "content_access": "link_only",
  "capture_method": "link-plus-user-context",
  "content_ref": null,
  "table_ref": null,
  "analysis_ref": null,
  "evidence_policy": "External source is supporting context only; PM confirmation is required before it becomes a decision.",
  "extracted_points": [],
  "risks": [
    "Video content was not directly inspected; PM must confirm which aspects to reference."
  ],
  "provider_metadata": {
    "provider": "bilibili",
    "capture_method": "link-plus-user-context",
    "content_access": "link_only",
    "needs_followup_confirmation": true
  }
}
```

Allowed values:

- `content_access`: `link_only`, `pm_summary`, `fetched_text`, `fetched_table`, `partial_fetch`
- `capture_method`: `link_only`, `link-plus-user-context`, `link-plus-summary`, `fetched_text`, `lark-doc`, `lark-sheet`
- `provider_metadata.content_access`: `link_only`, `pm_summary`, `fetched_text`, `fetched_table`, `partial_fetch`

## Write Path

Write the normalized record under:

```text
<KNOWLEDGE_REPO_PATH>/sessions/<session-name>/attachments/sources/<slug>.json
```

Where `<slug>` should be a short stable label such as
`bilibili-snake-game-reference`.

## Session Update Rules

When using this skill:

1. Register the Bilibili link as a source record.
2. Mark `provider_metadata.capture_method` as `link-plus-user-context`.
3. Preserve the PM's original wording in `raw_request`.
4. Preserve the PM's stated reference angle in `user_context` when available.
5. Add or keep explicit uncertainty in `risks` if the video was not directly
   inspected or fully interpretable.
6. Add only a short source-registration note to `conversation.md`.
7. Do not claim the video content was fully understood from the link alone.
8. Do not write inferred gameplay or feature conclusions into `notes.md` or
   `decisions.md` until the PM confirms them.

## Clarify Follow-up Rules

If the PM only says "make something like this video" or equivalent, `/clarify` must follow up on
which aspects to reference, for example:

- gameplay
- UI style
- animation
- interaction pattern
- scoring rules
- leaderboard or social mechanics
- levels or difficulty progression

Only PM-confirmed aspects may enter `notes.md` or `decisions.md`.

## Fallback Rules

If the link cannot be meaningfully inspected:

1. Still register the source as `bilibili_video`.
2. Keep the original link in `source_uri`.
3. Use PM-provided wording as `summary` or `user_context`.
4. Add risks such as:
   - `Video content was not directly inspected; PM must confirm which aspects to reference.`
   - `Shared browser context referenced a Bilibili video, but no reliable transcript or extracted summary was available.`
5. Continue clarification from the PM's stated intent instead of fabricating
   details.

## MVP Limits

For the MVP, this skill:

- does not write a crawler;
- does not promise subtitle, comment, danmu, or frame extraction;
- uses `link-plus-user-context` as the default capture strategy;
- treats the video as session enrichment only.

It must not:

- invent features from an uninspected video;
- mark a session `ready_for_goal: yes` from a video link alone;
- let external video content replace PM-confirmed IntentSpec fields.

## Example

PM says:

`Please look at this Bilibili video. I want a similar snake mini-program.`

Skill should:

1. Register the Bilibili URL as a source record.
2. Mark `capture_method` as `link-plus-user-context`.
3. Do not claim video content was understood.
4. Ask which aspects to reference: gameplay, UI, scoring, ranking, animation.
5. Only PM-confirmed aspects may enter `notes.md` / `decisions.md`.
