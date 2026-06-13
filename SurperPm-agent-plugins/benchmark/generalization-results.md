# Generalization Results

Sanitized public summary for the broad generalization runs. Raw
`benchmark/runs/` artifacts are intentionally not committed because they can
contain local paths, provider streams, Claude home files, debug logs, and
unredacted execution context.

## Source And Scope

| Suite | Source | Coverage | Public artifact |
|---|---|---:|---|
| `diverse-20` | rounds 014-033 review summaries | 20 repos / 20 cases | This file + `diverse20.json` + `cases/DV-*.md` |
| `app-50` | rounds 034-094 review summaries | 49 reviewed repos / 50 planned cases | This file + `app50.json` + `cases/AP-*.md` |

`AP-47` was defined in the case set but no sanitized latest review summary was
available in the reviewed local artifacts, so it is reported as missing rather
than counted as pass.

## Aggregate Summary

| Suite | Attempts | Distinct Cases Reviewed | Auto Pass | Needs Review | Fail | Infra Error | Missing |
|---|---:|---:|---:|---:|---:|---:|---:|
| `diverse-20` | 20 | 20 | 20 | 0 | 0 | 0 | 0 |
| `app-50` | 59 | 49 | 44 | 11 | 3 | 1 | 1 |
| `app-50` latest reviewed state | 49 | 49 | 36 | 10 | 3 | 0 | 1 |

Interpretation rules:

- `pass` means the auto-review found durable changes or verified no-op evidence
  and did not detect dependency/lockfile pollution, backend-scope violation, or
  forbidden path changes.
- `needs_review` means the run did not produce enough automated evidence for a
  pass/fail decision, most often because no git changes were detected.
- `fail` is mostly useful as optimization evidence: it exposed lockfile hygiene
  problems on large JavaScript/TypeScript repos.
- These are generalization stress results, not a replacement for Conduit MVP
  end-to-end acceptance.

## Latest Reviewed Case State

| Case | Round | Status | Changes | Dependency Changed | Scope Violation | Auto-review note |
|---|---:|---|---|---|---|---|
| AP-01 | 045 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-02 | 046 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-03 | 047 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-04 | 048 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-05 | 049 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-06 | 050 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-07 | 051 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-08 | 052 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-09 | 053 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-10 | 054 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-11 | 055 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-12 | 056 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-13 | 057 | fail | true | true | false | forbidden paths touched: package-lock.json |
| AP-14 | 058 | fail | true | true | false | forbidden paths touched: yarn.lock |
| AP-15 | 059 | needs_review | false | false | false | no git changes detected |
| AP-16 | 060 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-17 | 061 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-18 | 062 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-19 | 063 | needs_review | false | false | false | no git changes detected |
| AP-20 | 064 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-21 | 065 | needs_review | false | false | false | no git changes detected |
| AP-22 | 066 | fail | true | true | false | forbidden paths touched: pnpm-lock.yaml |
| AP-23 | 067 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-24 | 068 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-25 | 069 | needs_review | false | false | false | no git changes detected |
| AP-26 | 070 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-27 | 071 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-28 | 072 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-29 | 073 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-30 | 074 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-31 | 075 | needs_review | false | false | false | no git changes detected |
| AP-32 | 076 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-33 | 077 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-34 | 078 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-35 | 079 | needs_review | false | false | false | no git changes detected |
| AP-36 | 080 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-37 | 081 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-38 | 082 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-39 | 083 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-40 | 084 | needs_review | false | false | false | no git changes detected |
| AP-41 | 085 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-42 | 086 | needs_review | false | false | false | no git changes detected |
| AP-43 | 087 | needs_review | false | false | false | no git changes detected |
| AP-44 | 088 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-45 | 089 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-46 | 090 | needs_review | false | false | false | no git changes detected |
| AP-47 | - | missing | - | - | - | no sanitized latest review summary available |
| AP-48 | 092 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-49 | 093 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| AP-50 | 094 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-01 | 014 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-02 | 015 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-03 | 016 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-04 | 017 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-05 | 018 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-06 | 019 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-07 | 020 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-08 | 021 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-09 | 022 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-10 | 023 | pass | false | false | false | verified no-op; requested behavior already exists |
| DV-11 | 024 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-12 | 025 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-13 | 026 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-14 | 027 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-15 | 028 | pass | false | false | false | verified no-op; requested behavior already exists |
| DV-16 | 029 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-17 | 030 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-18 | 031 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-19 | 032 | pass | true | false | false | git changes present; oracle not fully verified automatically |
| DV-20 | 033 | pass | true | false | false | git changes present; oracle not fully verified automatically |

## Optimization Signals Extracted

| Signal | Evidence | Plugin hardening derived from it |
|---|---|---|
| Setup-only lockfile churn can create false changes in large JS/TS repos | AP-13, AP-14, AP-22 failed on `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` | `run-tests`, `submit-pr`, and `acceptance-review` now include explicit lockfile hygiene gates |
| Some large repos need early durable commits and narrower vertical slices | AP `needs_review` cases mostly showed no durable git changes | `repo-explorer` and `coding` now emphasize large-monorepo discipline and commit-early behavior |
| Default branch detection must not assume `main` or `master` | app-50 includes repos with varied default branches | benchmark finalization now detects `origin/HEAD`, common branch names, and HEAD movement |
| Timeouts and child process cleanup matter for long soaks | early app-50 restarts hit hung/orphaned processes | benchmark runner now uses explicit polling plus non-fatal process-tree cleanup |

