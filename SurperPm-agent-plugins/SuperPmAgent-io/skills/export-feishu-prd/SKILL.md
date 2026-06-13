---
name: SuperPmAgent-export-feishu-prd
description: Export a clarified session into a Feishu PRD deliverable record and register the generated artifact back into the session. Use after `notes.md` and `decisions.md` are stable enough for document sharing.
argument-hint: "session name plus destination details or generated Feishu document link"
---

# Export Feishu PRD

Turn a clarified SuperPmAgent session into a Feishu PRD artifact record.

This skill is a post-clarification delivery step. It does not replace the
session. It publishes a derived document-shaped artifact and records that
output back into the same session.

## Use When

Use this skill when:

- the PM wants a shareable PRD in Feishu/Lark;
- `notes.md` already contains a stable IntentSpec;
- `decisions.md` already captures confirmed PM boundaries;
- the output is meant for collaboration, review, or circulation outside the
  raw session files.

## Inputs

- `session_name`
- Feishu destination details or a generated Feishu document link
- Optional title override

## Source Of Truth

Read from the session in this order:

1. `notes.md`
2. `decisions.md`
3. `conversation.md` only as supporting context

The exported PRD must reflect the session, not override it.

Like `export-ppt`, this skill produces a derived artifact. It cannot
replace `notes.md`, and `/goal` must still consume the session rather than the
Feishu PRD link.

## Output Goal

Produce and register a normalized output record that follows
the session I/O protocol document in this repo.

## Required Output Record

```json
{
  "record_type": "derived_output",
  "output_type": "feishu_prd",
  "title": "PRD: phone field",
  "artifact_uri": "https://example.com/doc",
  "source_session": "<KNOWLEDGE_REPO_PATH>/sessions/add-phone-field-20260613",
  "source_files": [
    "notes.md",
    "decisions.md"
  ],
  "summary": "Derived Feishu PRD artifact for stakeholder review.",
  "risks": [
    "Feishu document formatting may evolve outside the session."
  ],
  "provider_metadata": {
    "provider": "feishu",
    "artifact_kind": "prd_doc"
  },
  "generated_at": "2026-06-13Z"
}
```

## Write Path

Write the artifact metadata record under:

```text
<KNOWLEDGE_REPO_PATH>/sessions/<session-name>/attachments/exports/<slug>.json
```

Where `<slug>` should be a short stable label such as `feishu-prd` or
`feishu-prd-v2`.

## Session Update Rules

When using this skill:

1. Keep `notes.md` as the executable IntentSpec for `/goal`.
2. Do not replace `notes.md` with the Feishu doc link.
3. Register the artifact in `attachments/exports/`.
4. Add a short note to `conversation.md` or `decisions.md` only when useful for
   auditability or working agreement.
5. If the exported PRD introduces a new PM-confirmed boundary, record that in
   `decisions.md`.
6. Keep the Feishu PRD positioned as a derived artifact, not a source-of-truth
   replacement for the session.

## Suggested PRD Mapping

A first-pass Feishu PRD should map session fields like this:

- `Raw Request` -> background or original ask
- `Standardized Goal` -> PRD objective
- `User Value` -> user or business value
- `Scope` -> included scope
- `Out of Scope` -> exclusions
- `Acceptance Criteria` -> acceptance or validation section
- `Constraints` -> implementation constraints
- `Risks` -> known risks

## MVP Limits

For the first implementation wave, this skill should:

- treat Feishu as a linked deliverable target;
- prefer recording the generated link over storing copied PRD content locally;
- remain deterministic about which session files it used.

It should not:

- silently mutate `notes.md` into a PRD;
- treat the external PRD as the new `/goal` source of truth;
- publish from a session whose scope is still materially unresolved.
