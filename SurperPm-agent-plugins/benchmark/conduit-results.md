# Conduit Results

Sanitized public summary for the Conduit practice runs. Raw
`benchmark/runs/` artifacts are intentionally not committed because they can
contain local paths, provider streams, Claude home files, debug logs, and
unredacted execution context.

## Source And Scope

| Track | Source | Public artifact |
|---|---|---|
| Conduit L1/L2/L3 | rounds 001-013 review summaries and selected graded notes | This file + `metrics.md` + `cases/L*.md` |
| Web contract probes | rounds 007-013 contract summaries | `metrics.md` + `cases/WEB-*.md` |
| Cross-repo code probes | rounds 007-013 XC summaries | `metrics.md` + `cases/XC-*.md` |

Conduit is the competition MVP path: it verifies that SuperPmAgent can go from a PM
goal to scoped implementation, verification evidence, and a PR/commit handoff on
a real full-stack target.

## Key Graded Evidence

| Case | Latest graded evidence | Status | Why it matters |
|---|---|---|---|
| `L1-01` | round-005 / round-008 graded notes | pass | Frontend-only change; proved backend/dependency guardrails after early lockfile pollution. |
| `L2-01` | round-005 / round-008 graded notes | pass | Cross-stack field propagation (`coverImage`) across model/API/UI. |
| `L3-03` | round-005 / round-008 graded notes | pass | Contradiction gate: no fake implementation when requirements conflict. |
| `XC-01..03` | round-008 / round-013 summaries | pass | Code skill generalizes beyond Conduit on Python/React/Node probes. |
| `WEB-01..04` | round-007 / round-013 summaries | pass | Plugin load, ready/not-ready session gates, and learnings injection contract. |

The latest raw Conduit smoke records in later AP rounds can show `needs_review`
because they were lightweight artifact probes with no intended code change. They
are not used as the primary Conduit grade.

## Aggregate Signals

| Area | Evidence | Optimization outcome |
|---|---|---|
| Frontend-only scope guard | `L1-01` round-004 failed on dependency/lockfile pollution (`jsdom` setup churn) | Added lockfile hygiene to `run-tests`, `submit-pr`, and `acceptance-review`. |
| Cross-stack propagation | `L2-01` needed model/API/form/list/detail consistency | Strengthened `SuperPmAgent-business/add-db-field` and `add-ui-form` propagation checklists. |
| Contradictory requirements | `L3-03` must stop and clarify instead of coding fake idempotency | Added the contradiction gate and explicit `clarify_needed` / `blocked` delivery states. |
| PR permission vs coding success | XR/XC runs could produce local changes while push/PR was blocked | Added `commit_ready` classification and `effective-exit` handling for submit blockers. |
| Web runtime contract | WEB probes validate plugin paths, session readiness, and learnings boundaries | Aligned `find`, `goal`, and `SuperPmAgent-web` with two knowledge loops. |

## Upload Policy

Commit these Conduit artifacts:

- `cases/L*.md`, `cases/XC-*.md`, and `cases/WEB-*.md`
- `conduit-results.md`
- `metrics.md`
- selected redacted excerpts only when a claim needs deeper evidence

Do not commit full raw run folders, Claude homes, debug logs, local `.env`
files, or provider streams.

