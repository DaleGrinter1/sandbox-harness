# PLAN_plugin-first-product

## Purpose / Big Picture

Make the `modal-sandbox` Codex plugin the primary product entry point for coding agents while preserving the existing Python SDK and JSON CLI as its tested execution engine.

## Surprises & Discoveries

- The repository already had maintainer-oriented skills, but no distributable end-user plugin.
- The CLI's `schema --agent` contract already provides the runtime workflow discovery the public skill needs, so the plugin does not need bundled command references or an MCP server.

## Decision Log

- 2026-07-23: Keep the SDK and CLI public and compatible, but reposition them as the plugin's engine and an advanced direct-use surface.
- 2026-07-23: Ship one concise end-user skill and keep `.agents/skills/` as repository-maintenance guidance.
- 2026-07-23: Require an installed `sandbox` command; do not silently install, use `uvx`, or bundle duplicate Python code.
- 2026-07-23: Use capability discovery through CLI schema version 1 rather than pinning the plugin to one package release.

## Outcomes & Retrospective

The repository now distributes a validated `modal-sandbox` plugin with one
end-user skill, repo-local marketplace metadata, plugin-first product docs, and
plugin-aware release checks. The existing SDK and CLI remain compatible and
all default validation remains resource-free. Installing the repo-local
marketplace and opening a new Codex thread is the final user-controlled
acceptance step because it changes personal Codex configuration.

## Context and Orientation

- `plugins/modal-sandbox/`
- `.agents/plugins/marketplace.json`
- `packages/sandbox_cli/cli.py`
- `tests/test_packaging.py`
- `docs/references/development.md`

## Plan of Work

Scaffold and validate the repo-local plugin and skill, reposition the product documentation and agent manifest, add plugin-aware packaging and release checks, then validate all changes without creating Modal resources.

## Concrete Steps

1. Create the plugin, public skill, skill interface metadata, and repo-local marketplace entry.
2. Add packaging tests for manifest identity, marketplace wiring, CLI prerequisite, safety boundaries, and workflow selection.
3. Update product, architecture, agent, development, and release documentation.
4. Extend release checks with skill and plugin validation.
5. Regenerate the agent manifest and run no-resource validation.

## Machine State

Implementation state is stored beside this plan:

- `state/feature-list.json`
- `state/session-state.json`
- `state/progress.jsonl`

## Progress

Use `state/progress.jsonl` for detailed checkpoints.

## Testing Approach

Run focused packaging tests and creator validators first, followed by schema generation, the repository no-resource checks, release readiness, and the exec-plan validator. Live Modal smoke tests remain opt-in and are not part of default validation.

## Constraints & Considerations

- Preserve all existing Python imports, CLI commands, and JSON envelopes.
- Keep discovery resource-free and require explicit authorization for live Modal actions.
- Do not add MCP, app, hook, or branding artifacts to the v1 plugin.
- Keep plugin and package versions independently releasable while testing against CLI schema version 1.
