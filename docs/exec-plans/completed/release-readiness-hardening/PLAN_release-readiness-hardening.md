# PLAN_release-readiness-hardening

## Purpose / Big Picture

Complete the remaining release-readiness next steps for `modal-sandbox-sdk`
after the 0.2.0 release candidate prep. When this work is complete, the CLI
will reject known-invalid lifecycle/configuration combinations before creating
Modal resources, product specs will cover the shipped public surfaces, CI will
validate exec-plan state, and the generated CLI schema contract will be checked
in the default test suite.

## Surprises & Discoveries

- 2026-06-16: Live Modal acceptance was already run by the maintainer and
  passed: `6 passed in 297.88s`.
- 2026-06-16: `uv.lock` tracks the editable package version, so the 0.2.0
  version bump belongs in the release-prep diff.

## Decision Log

- 2026-06-16: Use one short active initiative because this touches CLI
  behavior, product specs, CI, and release governance together.
- 2026-06-16: Keep live Modal tests opt-in; default validation must remain
  resource-free.

## Outcomes & Retrospective

Completed on 2026-06-16. The CLI now rejects invalid lifecycle combinations
and global configuration before sandbox creation, product specs cover the major
0.2.0 public surfaces, `docs/generated/cli-schema.json` is checked against the
runtime schema, and CI validates exec-plan state. The release candidate remains
resource-free by default; live Modal acceptance was already recorded separately.

## Context and Orientation

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/PLANS.md`
- `docs/exec-plans/index.md`
- `docs/product-specs/index.md`
- `packages/sandbox_cli/cli.py`
- `tests/test_cli.py`
- `.github/workflows/tests.yml`

## Plan of Work

First, harden CLI argument validation where bad input or lifecycle mismatch can
be rejected before sandbox creation. Then add product specs for the shipped
public surfaces that are currently only represented in README/reference docs.
Next, add a generated CLI schema contract check and wire exec-plan validation
into CI. Finally, run the default release-readiness validation suite and update
the state files with evidence.

## Concrete Steps

1. Add CLI preflight checks for `snapshot`, `domain`, workspace path, timeouts,
   ports, and output limits.
2. Extend CLI tests so preflight failures do not instantiate `Sandbox`.
3. Add product specs for CLI workflows, volume-backed snapshots, and
   Vercel-style conveniences.
4. Add generated schema contract validation to tests or generated docs.
5. Add `./scripts/execplan/check.sh` to CI.
6. Run focused and full validation.
7. Mark feature state as passing only with evidence.

## Machine State

Implementation state is stored beside this plan:

- `state/feature-list.json` is the canonical implementation checklist.
- `state/session-state.json` tracks active work and handoff.
- `state/progress.jsonl` is append-only checkpoint evidence.

## Progress

Initial plan created on 2026-06-16.

Completed release-readiness hardening on 2026-06-16 after final validation.

## Testing Approach

Default validation must not create real Modal resources:

```bash
uv run pytest tests/test_cli.py tests/test_packaging.py
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv build
uv run sandbox --help
uv run sandbox schema
./scripts/execplan/check.sh
```

Live Modal validation is already recorded for this release candidate and will
not be rerun unless explicitly requested.

## Constraints & Considerations

- Keep Modal imported lazily.
- Discovery commands must not instantiate `Sandbox`.
- CLI output remains JSON except `--help` and `--version`.
- Nonzero sandbox command exits remain `CommandResult.exit_code`.
- Do not create legacy markdown task files or `tasks/` directories.
