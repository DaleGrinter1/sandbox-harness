# PLAN_assessment-remediation

## Purpose / Big Picture

Address assessment feedback by improving release readiness, local hooks, agent handoff guidance, exception clarity, and high-cognitive-load SDK internals while preserving the existing public API and Modal safety rules.

## Surprises & Discoveries

- `packages/sandbox/sandbox.py` and `packages/sandbox/provider_modal.py` both mix public facade/provider behavior with pure validation and error translation helpers.
- `.pre-commit-config.yaml` already exists, but it only covers fast local checks.
- CI already builds and smoke-installs the wheel; release publishing infrastructure is not yet defined.

## Decision Log

- 2026-07-13: Treat PyPI work as release readiness and trusted-publishing setup, not an immediate package publish.
- 2026-07-13: Treat subagents as repo-local agent workflow lanes and skills, not a runtime agent framework.
- 2026-07-13: Reduce cognitive load with a few deep private helper modules rather than many shallow files.

## Outcomes & Retrospective

Fill in when the initiative is complete.

## Context and Orientation

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/PRODUCT_SENSE.md`
- `docs/references/cli.md`
- `docs/references/agents.md`
- `packages/sandbox/sandbox.py`
- `packages/sandbox/provider_modal.py`
- `packages/sandbox/errors.py`
- `.pre-commit-config.yaml`
- `.github/workflows/tests.yml`

## Plan of Work

First create durable state for the initiative. Then harden hooks and release checks, refactor validation/error helpers out of the largest SDK files, update docs for agent handoff and release workflow, and run focused validation before closing the work.

## Concrete Steps

1. Add and validate exec-plan state files.
2. Add hook coverage for release checks without making normal commits unreasonably slow.
3. Add release-check scripting and PyPI trusted-publishing workflow docs/configuration.
4. Move pure validation helpers from `sandbox.py` into one private SDK helper module.
5. Move provider error translation helpers from `provider_modal.py` into one private provider helper module.
6. Add or update tests for public imports, exception mapping, and package release metadata.
7. Update agent, development, and cognitive-load docs.
8. Run focused tests and the exec-plan validator.

## Machine State

Implementation state is stored beside this plan:

- `state/feature-list.json`
- `state/session-state.json`
- `state/progress.jsonl`

## Progress

Use `state/progress.jsonl` for detailed checkpoints.

## Testing Approach

Default validation must not create real Modal resources. Use focused tests first:

```bash
uv run pytest tests/test_sandbox.py tests/test_provider_modal.py tests/test_packaging.py
uv run ruff format --check .
uv run ruff check .
uv run pyright
./scripts/execplan/check.sh
```

Run release checks after packaging changes:

```bash
./scripts/dev/release-check.sh
```

## Constraints & Considerations

- Keep Modal imported lazily.
- Preserve public imports and CLI behavior.
- Nonzero sandbox command exits stay as `CommandResult.exit_code`.
- Live Modal tests remain opt-in only.
- Avoid adding token placeholders or secrets to docs, tests, or workflow files.
