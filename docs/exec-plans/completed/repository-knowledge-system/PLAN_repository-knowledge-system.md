# PLAN_repository-knowledge-system

## Purpose / Big Picture

Make the repository itself the canonical source for agent execution context, architecture, product intent, and execution tracking. Keep `AGENTS.md` as a concise map and move durable details into `docs/`.

## Surprises & Discoveries

- The requested reference file `/Users/ibrahimsaidi/Desktop/Builds/cloudflare_builds/orange/docs/PLANS.md` was not present on this machine, so this repo-local guide was adapted from the public source material and current repo needs.
- The repo later pivoted repo-local skills to the Vercel-compatible `.agents/skills/` project path.

## Decision Log

- 2026-06-09: Use `docs/exec-plans/active/<initiative>/state/*.json*` for machine state and disallow markdown task files by default.
- 2026-06-09: Keep `.agents/skills` as repo-local development helpers; it is not the deprecated dot-agent planning directory.
- 2026-06-09: Rehome user-facing workflow docs under `docs/references/` and compatibility design notes under `docs/design-docs/`.

## Outcomes & Retrospective

Pending. Complete this section when the initiative moves to `docs/exec-plans/completed/`.

## Context and Orientation

Read:

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/PLANS.md`
- `docs/exec-plans/index.md`
- `docs/design-docs/core-beliefs.md`
- `docs/references/development.md`

## Plan of Work

Scaffold the target knowledge-store layout, rehome existing docs, seed execution-plan state files, add validation scripts, and rewrite legacy references.

## Concrete Steps

1. Create required docs directories and governance files.
2. Move tracked docs with `git mv` where possible.
3. Add the execution plan template and active initiative state files.
4. Add validation scripts for active initiative state.
5. Rewrite links and legacy references.
6. Run exec-plan validation and repository tests.

## Machine State

- `state/feature-list.json` is the canonical implementation checklist.
- Every feature starts with `"passes": false`.
- `state/session-state.json` tracks the active feature, blockers, next action, and handoff rules.
- `state/progress.jsonl` is append-only and records meaningful checkpoints with structured evidence.

## Progress

See `state/progress.jsonl`.

## Testing Approach

Run:

```bash
./scripts/execplan/check.sh
uv run pytest tests/test_packaging.py
```

Use broader tests when code behavior changes. Default tests must not create real Modal resources.

## Constraints & Considerations

- Do not create the legacy dot-agent planning directory or the legacy top-level specs directory.
- Do not create active markdown task files.
- Preserve history with `git mv` when tracked source files are still present.
- Keep `AGENTS.md` short and map-style.
