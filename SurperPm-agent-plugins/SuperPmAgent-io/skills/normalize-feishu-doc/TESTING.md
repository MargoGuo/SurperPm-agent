# Normalize Feishu Doc Testing

This document describes how to manually verify the MVP Feishu input flow for
`normalize-feishu-doc`.

The purpose of the test is not to validate full Feishu parsing fidelity. The
purpose is to verify that a Feishu document can become a usable SuperPmAgent session
source record and then support `/clarify`.

## Test Scope

This test plan verifies:

- Feishu document URLs are treated as `feishu_doc`, not generic `url`.
- A normalized source record is created under `attachments/sources/`.
- `/clarify` continues from the registered source record.
- Fallback behavior is explicit when Feishu content cannot be fetched.

This test plan does not verify:

- full rich-text fidelity;
- image extraction;
- attachment download;
- downstream Feishu PRD export.

## Preconditions

Before testing, ensure:

1. The SuperPmAgent plugin set including `SuperPmAgent-core` is installed in Claude.
2. The active environment can use Lark skills.
3. `lark-cli` is available.
4. Lark auth is already configured, or the tester is prepared to complete auth.
5. A real Feishu/Lark document URL is available.
6. A writable session path is available under `<KNOWLEDGE_REPO_PATH>/sessions/`.

## Recommended Test Session

Use a dedicated test session name such as:

```text
feishu-doc-test-20260613
```

## Happy Path Test

### Input

Use a prompt shaped like:

```text
/SuperPmAgent-core:clarify --session feishu-doc-test-20260613
这是我们的需求文档，请基于这个飞书文档帮我整理成可执行的需求 session：
<Feishu 文档链接>
重点关注 scope、acceptance criteria 和 out of scope。
```

### Expected Behavior

The flow should do all of the following:

1. Recognize that the link is a Feishu/Lark document.
2. Prefer `normalize-feishu-doc` over generic URL normalization.
3. Use Lark read capabilities to inspect the document when possible.
4. Create or update a normalized source record under:

```text
<KNOWLEDGE_REPO_PATH>/sessions/feishu-doc-test-20260613/attachments/sources/
```

5. Continue `/clarify` and update:
   - `conversation.md`
   - `notes.md`
   - `decisions.md`

### Expected Source Record Checks

The `attachments/sources/*.json` file should satisfy these checks:

- `source_type` is exactly `feishu_doc`
- `source_uri` is the original Feishu link
- `title` is not empty when the document title is available
- `summary` is short and reviewable
- `raw_request` keeps the PM wording when available
- `extracted_points` contains a few useful requirement points
- `risks` contains uncertainty when the document appears draft-like
- `provider_metadata.provider` is `feishu`

### Expected Session Checks

- `conversation.md` contains a short registration note for the Feishu source
- `notes.md` contains structured IntentSpec content, not a raw document dump
- `decisions.md` contains only confirmed boundaries
- `ready_for_goal` is set according to clarity completeness, not simply because
  a Feishu link exists

## Fallback Test: Auth Or Permission Failure

### Input

Repeat the same test with one of:

- a Feishu document the current identity cannot access;
- an environment where Lark auth is missing;
- a malformed but still Feishu-looking document URL.

### Expected Behavior

The flow should still:

1. Register the source as `feishu_doc`
2. Preserve the original link in `source_uri`
3. Use PM-supplied context as `summary` when possible
4. Add an explicit fetch or permission risk
5. Continue clarification without pretending the document was fully parsed

### Expected Fallback Risk Examples

At least one risk should look like:

- `Feishu content could not be fetched during normalization`
- `Document access may require additional auth or permission`

## Negative Test: Should Not Happen

The following outcomes should be treated as failures:

- The link is stored as generic `url` when it is clearly a Feishu document
- The full raw document body is copied into `notes.md`
- `ready_for_goal` becomes `yes` only because a document link exists
- `decisions.md` contains unconfirmed extracted guesses
- The flow silently drops the Feishu source when fetch fails

## Manual Review Checklist

After each run, review:

- Was the correct session used?
- Was a `feishu_doc` source file created?
- Did `notes.md` stay structured and bounded?
- Did `risks` honestly describe uncertainty?
- Did the flow degrade safely when Feishu fetch was unavailable?

## MVP Exit Criteria

The Feishu input MVP is good enough when:

1. A readable Feishu link can become a normalized source record.
2. `/clarify` can continue from that record.
3. Failure to fetch does not break the session flow.
4. The session remains the source of truth for `/goal`.
