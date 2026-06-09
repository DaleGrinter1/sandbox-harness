# Exec Plans Index

Execution plans are durable artifacts for long-running or cross-cutting work.

## Active

No active initiatives are currently tracked.

## Completed

- [Repository Knowledge System](completed/repository-knowledge-system/PLAN_repository-knowledge-system.md)

## Workflow Summary

- Use markdown for narrative plans.
- Use `state/feature-list.json` for implementation checklist state.
- Use `state/session-state.json` for active feature, blockers, next action, and handoff.
- Use `state/progress.jsonl` for append-only checkpoints.
- Do not use markdown task files by default.

Validate with:

```bash
./scripts/execplan/check.sh
```
