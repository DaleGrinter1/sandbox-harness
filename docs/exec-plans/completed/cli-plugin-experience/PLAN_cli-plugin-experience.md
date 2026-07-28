# PLAN_cli-plugin-experience

## Purpose / Big Picture

Improve the day-to-day CLI and plugin experience so users and agents can move
from safe discovery to live work with more confidence and less repeated flag
entry. This initiative implements the recommendation list: `status`,
`cleanup`, plugin preview-before-live behavior, clearer preflight summaries,
and project-level config.

Success means users can inspect visible Modal sandbox apps, preview cleanup
before stopping resources, see resolved live behavior before execution, reuse
project defaults through `sandbox.toml`, and receive plugin preflight output
that explains the next action clearly.

## Surprises & Discoveries

- Modal CLI 1.5 exposes `modal app list --json` and `modal app stop --yes
  APP_IDENTIFIER`, which gives the package a supported low-complexity path for
  status and cleanup.
- Cleanup should not guess. The implemented CLI defaults to dry-run output and
  requires `--yes` before stopping Modal apps.
- The repo-local CLI workflow skill still used the old
  `credentials.authenticated` doctor field, so this initiative updates that
  guidance as part of the plugin experience.

## Decision Log

- 2026-07-28: Implement `status` as read-only Modal app inspection. It contacts
  Modal but does not create resources.
- 2026-07-28: Implement `cleanup` as explicit app stopping only. It requires
  `--yes`; dry-run output is the default.
- 2026-07-28: Use `sandbox.toml` to fill omitted global CLI flags, with
  explicit CLI arguments taking precedence.
- 2026-07-28: Make the plugin preflight run one resource-free preview command
  and make benchmark scenarios record preview metadata before live runs.

## Outcomes & Retrospective

The recommendation list is implemented and validated without creating Modal
resources. The CLI now includes `status` for read-only Modal app inspection,
`cleanup` with dry-run output by default and `--yes` for explicit stops,
`sandbox.toml` project config with CLI flag override behavior, and generated
schema/agent-manifest entries for resource management and config. The plugin
preflight now returns a clearer summary and runs a resource-free preview; the
benchmark helper records preview metadata before live scenario runs. Public and
repo-local skills now tell agents to preview before live work and to avoid
cleanup execution without explicit authorization.

Live Modal validation was not run because the user did not explicitly
authorize live resource operations during this implementation.

## Context and Orientation

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/PRODUCT_SENSE.md`
- `docs/references/cli.md`
- `plugins/modal-sandbox/skills/modal-sandbox/SKILL.md`
- `packages/sandbox_cli/cli.py`
- `packages/sandbox_cli/schema.py`
- `plugins/modal-sandbox/scripts/preflight.py`
- `plugins/modal-sandbox/scripts/benchmark.py`
- `tests/test_cli.py`
- `tests/test_plugin_scripts.py`

## Plan of Work

1. Add `sandbox status` and `sandbox cleanup` with resource-conscious defaults,
   schema entries, docs, and tests.
2. Make plugin preflight easier to interpret and add a resource-free preview
   step before live workflows.
3. Add `sandbox.toml` project config for repeated global flags while preserving
   explicit CLI override behavior.
4. Update plugin skill guidance, repo-local CLI workflow skill, README, CLI
   reference, generated schema, and tests together.
5. Run resource-free validation. Do not run live Modal tests unless explicitly
   authorized.

## Concrete Steps

1. Add Modal app status helpers around `modal app list --json`.
2. Add cleanup helpers around `modal app stop --yes`, while keeping dry-run as
   the default.
3. Wire `status` and `cleanup` into the CLI parser, schema, generated
   contracts, docs, and tests.
4. Add project config loading from `sandbox.toml` for omitted global flags.
5. Update plugin preflight to include a clear summary and resource-free
   preview command.
6. Update benchmark execution to record preview metadata before live scenario
   runs.
7. Update public and repo-local plugin/CLI guidance.
8. Run focused tests, generated schema validation, full no-resource validation,
   release readiness, and exec-plan validation.

## Machine State

- `state/feature-list.json`
- `state/session-state.json`
- `state/progress.jsonl`

## Progress

Implementation and resource-free validation are complete. All features in
`state/feature-list.json` are passing with evidence.

## Testing Approach

Run focused tests first:

```bash
uv run pytest tests/test_cli.py tests/test_cli_schema.py tests/test_plugin_scripts.py tests/test_packaging.py
```

Then run:

```bash
./scripts/dev/schema.sh
uv run pyright
uv run ruff format --check .
uv run ruff check .
./scripts/execplan/check.sh
```

Before release or handoff, run:

```bash
./scripts/dev/check.sh
bash ./scripts/dev/release-check.sh
```

## Constraints & Considerations

- `status` may contact Modal but must not create resources.
- `cleanup` must not stop anything without `--yes`.
- Plugin preview-before-live must remain resource-free.
- Project config must never contain or print secret values; preview reports env
  keys only.
- Explicit CLI flags override `sandbox.toml`.
- Keep Modal imported lazily and default tests resource-free.
