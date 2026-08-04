# PLAN_plugin-maturity

## Purpose / Big Picture

Bring the `modal-sandbox` plugin to the same operational maturity as its CLI
and SDK engine. Agents should be able to select a representative workflow,
validate compatibility without creating resources, identify approval
boundaries, verify results, and clean up deliberately.

## Surprises & Discoveries

- The plugin already validates and distributes cleanly, but its examples cover
  only part of the CLI 0.4.1 workflow surface.
- The trigger corpus has a checked-in semantic review but no deterministic
  metric aggregator for repeatable forward-test results.
- Plugin 0.4.0 accepts CLI schema 1, while the richer source, filesystem,
  readiness, and resource-control workflows require the CLI 0.4.1 surface.

## Decision Log

- 2026-07-28: Keep the plugin as a guided orchestration layer; all live
  execution remains in the installed `sandbox` CLI.
- 2026-07-28: Emit workflow schema 2 and normalize schema 1 inputs for
  compatibility throughout the 0.4.x line.
- 2026-07-28: Make all default validation resource-free and retain one
  explicitly authorized, opt-in live plugin smoke test.
- 2026-07-28: Keep the public skill concise and move detailed recipes and
  recovery guidance into one-level-deep references.

## Outcomes & Retrospective

The plugin now provides ten versioned, CLI-validated workflows spanning the
important 0.4.1 capabilities. Workflow schema 2 makes compatibility,
approval, verification, recovery, and cleanup requirements explicit while
preserving schema 1 inputs throughout the 0.4.x line.

The public skill remains a short workflow router, with recipes and recovery
details loaded from focused references. Deterministic evaluation meets all
acceptance thresholds: precision 1.0, recall 1.0, workflow-selection accuracy
1.0, and zero unauthorized live actions.

Repository-independent fake-CLI tests, official validators, package release
checks, and the full resource-free suite pass. The live plugin smoke is
available as an explicit opt-in gate and was intentionally not run without
authorization or credentials.

## Context and Orientation

- `ARCHITECTURE.md`
- `docs/PRODUCT_SENSE.md`
- `docs/references/cli.md`
- `plugins/modal-sandbox/`
- `tests/test_plugin_scripts.py`
- `tests/test_plugin_distribution.py`
- `scripts/dev/release-check.sh`

## Plan of Work

First define and test the versioned workflow contract and resource-free
compatibility check. Then expand distributed workflows to cover the CLI 0.4.1
capability groups, revise the skill using progressive disclosure, add
repeatable evaluation metrics and forward tests, and finish with
repository-independent and release validation.

## Concrete Steps

1. Implement workflow schema 2 with schema 1 normalization and required
   capability validation.
2. Add a compatibility-check mode backed by preflight and
   `sandbox schema --agent`.
3. Add source-seeding, service-readiness, resource-control, and filesystem
   workflows; strengthen persistence and reuse verification.
4. Split detailed workflow and recovery guidance into skill references and
   align plugin metadata/versioning with CLI 0.4.1.
5. Add evaluation aggregation, behavioral tests, portable fake-CLI checks,
   release validation, and an opt-in live plugin smoke.
6. Run focused, full resource-free, release, skill, plugin, and exec-plan
   validation and record evidence.

## Machine State

Implementation state is stored beside this plan:

- `state/feature-list.json`
- `state/session-state.json`
- `state/progress.jsonl`

## Progress

All planned features are implemented and validated. Full resource-free
validation passed with 248 tests passing and 5 opt-in live tests skipped; the
release readiness check also passed.

## Testing Approach

Use fake CLI processes and direct Python tests for workflow normalization,
compatibility states, error handling, command contracts, and evaluation
metrics. Copy the plugin to a temporary directory for distribution checks.
Run full repository and release checks without creating Modal resources.

## Constraints & Considerations

- Preserve the current uncommitted CLI/provider refactor.
- Do not add an MCP server, app connector, or second execution engine.
- Do not silently install or upgrade packages.
- Do not contact Modal or stop resources during default validation.
- Live validation requires explicit authorization, unique resource names,
  bounded execution, and cleanup evidence.
