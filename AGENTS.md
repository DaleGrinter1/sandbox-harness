# AGENTS.md

## Read Order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/PLANS.md`
4. `docs/design-docs/index.md`
5. Relevant product spec under `docs/product-specs`
6. Relevant execution plan under `docs/exec-plans/active/`

## Canonical Path Map

- Architecture: `ARCHITECTURE.md`
- Product intent: `docs/PRODUCT_SENSE.md`, `docs/product-specs`
- Design docs: `docs/design-docs/`
- Execution plans: `docs/exec-plans/`
- Generated facts: `docs/generated/`
- References and migrated docs: `docs/references/`
- Quality, security, reliability: `docs/QUALITY_SCORE.md`, `docs/SECURITY.md`, `docs/RELIABILITY.md`
- Project skills: `.agents/skills/`

## Routing By Work Type

- Python SDK changes: read `ARCHITECTURE.md`, `docs/design-docs/core-beliefs.md`, then relevant files in `packages/sandbox/`.
- CLI changes: read `docs/references/cli.md`, `docs/exec-plans/index.md`, and update CLI schema/tests together.
- Modal provider changes: read `docs/references/modal-setup.md`, provider tests, and keep live Modal tests opt-in.
- Docs/governance changes: read `docs/PLANS.md`, `docs/design-docs/index.md`, and `docs/exec-plans/index.md`.
- Product/API behavior changes: read the index in `docs/product-specs` and update examples/docs.

## Execution Planning

For complex or long-running work, read in this order:

1. `docs/exec-plans/PLAN_TEMPLATE.md`
2. `docs/exec-plans/index.md`
3. The initiative `PLAN_<initiative>.md`
4. `state/session-state.json`
5. `state/feature-list.json`
6. `state/progress.jsonl`

Use markdown for the narrative plan only. Implementation checklist and handoff state live in JSON/JSONL state files.

## Deprecated Paths

- Do not create or use the legacy dot-agent planning directory.
- Do not create or use the legacy top-level specs directory; product specs live in `docs/product-specs`.
- Do not create markdown task files or `tasks/` directories for active work unless a human explicitly asks.

## Validation

- Default tests must not create real Modal resources.
- Run the narrowest useful command for code changes.
- Validate exec-plan state with `./scripts/execplan/check.sh`.
