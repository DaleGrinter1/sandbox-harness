# PLAN_plugin-first-product-experience

## Purpose / Big Picture

Make the plugin the main product experience while keeping the existing project
and package names unchanged. The CLI remains the JSON engine and the SDK stays
the lower-level Python implementation layer.

Success means a new user sees the plugin path first, agents have stronger
plugin acceptance contracts, common user intents have workflow examples, plugin
preflight exposes decision-friendly readiness fields, and plugin scripts provide
resource-free workflow orchestration without duplicating CLI or SDK behavior.

## Surprises & Discoveries

- The README and architecture already framed the plugin as the front door, so
  this work strengthens that stance without renaming.
- The plugin did not yet ship intent-based workflow examples or a resource-free
  workflow planning helper.
- The preflight summary had readiness data but not the product-like
  `safe_to_continue`, `next_action`, and `requires_user_approval` fields.

## Decision Log

- 2026-07-28: Keep all names unchanged per maintainer request.
- 2026-07-28: Add `workflow.py` as a resource-free orchestration helper. It
  validates distributed workflow examples and emits starter plans by intent.
- 2026-07-28: Keep plugin scripts as orchestration only. They do not run Modal
  directly and do not duplicate the Python SDK implementation.

## Outcomes & Retrospective

Completed without renaming the repo, package, CLI, plugin, or SDK. The plugin is
now framed as the main product surface, the CLI as the JSON execution engine,
and the SDK as the lower-level Python implementation layer.

Added distributed plugin workflow examples, a resource-free workflow planner,
decision-friendly preflight summary fields, plugin manifest copy, and stronger
acceptance/distribution tests. Validation stayed resource-free; live Modal
validation was not run because it requires explicit user authorization and
credentials.

## Context and Orientation

- `README.md`
- `ARCHITECTURE.md`
- `docs/PRODUCT_SENSE.md`
- `plugins/modal-sandbox/skills/modal-sandbox/SKILL.md`
- `plugins/modal-sandbox/scripts/preflight.py`
- `plugins/modal-sandbox/scripts/benchmark.py`
- `plugins/modal-sandbox/scripts/workflow.py`
- `plugins/modal-sandbox/examples/`
- `tests/test_plugin_acceptance.py`
- `tests/test_plugin_scripts.py`
- `tests/test_plugin_distribution.py`
- `tests/test_packaging.py`

## Plan of Work

1. Keep names unchanged.
2. Make plugin-first framing explicit in product docs and skill guidance.
3. Add plugin workflow examples for common user intents.
4. Add a resource-free workflow planning helper.
5. Strengthen plugin acceptance tests around preview, approval, cleanup, and
   prompt workflows.
6. Make preflight output more decision-friendly.
7. Validate without creating Modal resources.

## Concrete Steps

1. Add `plugins/modal-sandbox/scripts/workflow.py`.
2. Add workflow examples for safe tests, debugging, persistent workspaces,
   reusable coding sandboxes, benchmarks, and cleanup.
3. Update README, architecture, product sense, and public plugin skill to
   present plugin first while leaving names unchanged.
4. Add acceptance and distribution tests for workflow examples and planner.
5. Add preflight summary fields: `safe_to_continue`, `next_action`, and
   `requires_user_approval`.
6. Run focused plugin tests, full no-resource validation, release readiness,
   and exec-plan validation.

## Machine State

- `state/feature-list.json`
- `state/session-state.json`
- `state/progress.jsonl`

## Progress

Implementation is underway in the current workspace. Feature state records
validation evidence.

## Testing Approach

Focused plugin tests:

```bash
uv run pytest tests/test_plugin_acceptance.py tests/test_plugin_scripts.py tests/test_plugin_distribution.py tests/test_packaging.py
```

Full checks before handoff:

```bash
./scripts/dev/check.sh
bash ./scripts/dev/release-check.sh
./scripts/execplan/check.sh
```

## Constraints & Considerations

- Do not rename the repo, package, CLI, plugin, or SDK.
- Do not duplicate SDK behavior inside plugin scripts.
- Do not create Modal resources during default validation.
- Live Modal commands and cleanup execution still require explicit user
  approval.
