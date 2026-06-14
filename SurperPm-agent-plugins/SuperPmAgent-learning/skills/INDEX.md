# SuperPmAgent-learning skills index

Used by `SuperPmAgent-core`'s `find` skill to discover available learning skills.

| Skill | Keywords | When to use |
|---|---|---|
| distill-goals | distill, extract, learnings, knowledge, summarize | After goal executions complete — extract reusable knowledge |
| cleanup-workdirs | cleanup, workdir, disk, residual, garbage | Periodically remove stale execution workdirs |
| cleanup-knowledge | cleanup, orphan, stale, data, logs | Remove orphan data, fix inconsistencies in .logs/ |
| archive-learnings | archive, decay, score, expired, prune | Batch-archive learnings below retention threshold |
| sync-knowledge | sync, git, pull, push, knowledge | Force bidirectional knowledge repo sync |

## Recommended scheduled goals

```
Knowledge Distill     — schedule: "24"  — runs daily
Workdir Cleanup       — schedule: "12"  — runs twice daily
Knowledge Maintenance — schedule: "168" — runs weekly (archive + cleanup + sync)
```
