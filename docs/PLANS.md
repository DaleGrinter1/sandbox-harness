# Execution Plans

This repository uses Harness-style execution plans for work that spans multiple files, multiple sessions, or non-obvious decisions.

## Source Of Truth

- Narrative plan: `docs/exec-plans/active/<initiative>/PLAN_<initiative>.md`
- Implementation checklist: `docs/exec-plans/active/<initiative>/state/feature-list.json`
- Session handoff: `docs/exec-plans/active/<initiative>/state/session-state.json`
- Progress log: `docs/exec-plans/active/<initiative>/state/progress.jsonl`

Markdown explains intent and decisions. JSON/JSONL tracks implementation state.

## When To Create A Plan

Create an active initiative when work:

- touches architecture, public API, CLI contract, or docs governance;
- may span multiple agent sessions;
- needs durable progress handoff;
- has multiple features that require independent verification.

Small one-turn fixes can use an ephemeral chat plan and do not need files.

## Workflow

1. Copy `docs/exec-plans/PLAN_TEMPLATE.md` into `docs/exec-plans/active/<initiative>/PLAN_<initiative>.md`.
2. Create `state/feature-list.json`, `state/session-state.json`, and `state/progress.jsonl`.
3. Add every feature with `"passes": false`.
4. Work on one active feature at a time.
5. Append meaningful checkpoints to `progress.jsonl`.
6. Update `session-state.json` before handoff.
7. Mark `passes: true` only after evidence-backed validation.
8. Move completed initiatives to `docs/exec-plans/completed/`.

Do not create markdown task files or `tasks/` directories by default.

## Validation

Run:

```bash
./scripts/execplan/check.sh
```

This validates active initiative shape, required plan sections, JSON state, JSONL progress, feature references, and deprecated task directories.

## Doc Gardening

This platform does not provide a recurring automation scheduler from inside the repo. Run this manual weekly process:

```bash
./scripts/execplan/check.sh
rg -n "legacy dot-agent|legacy top-level specs" .
rg -n "docs/(cli|development|modal-setup)\\.md|docs/vercel-compat\\.md" README.md docs AGENTS.md
```

Then review:

- stale docs under `docs/design-docs/` and `docs/references/`;
- active initiatives with no recent progress;
- broken local markdown links;
- quality score action items in `docs/QUALITY_SCORE.md`.
