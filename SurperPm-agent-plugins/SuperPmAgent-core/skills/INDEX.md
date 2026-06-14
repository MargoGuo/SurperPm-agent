# SuperPmAgent Core Skills

SuperPmAgent-core has no standalone skills. It provides two commands (`goal`, `clarify`) and two hooks (`pre-tool-use`, `stop`).

Resource discovery is handled by the global CLAUDE.md prompt via directory conventions (`SuperPmAgent-*/skills/INDEX.md`). Extension injection is handled by the `pre-tool-use.py` hook. Knowledge distillation is a scheduled Goal using the `SuperPmAgent-learning` plugin.
