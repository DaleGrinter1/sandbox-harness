# PLAN_public-plugin-onboarding

## Purpose / Big Picture

Make the public `modal-sandbox` plugin installable from GitHub and guide a new user from installation to a safe first-run preview in under five minutes.

## Surprises & Discoveries

- PyPI now provides the CLI, but `pip install` may not place user-level scripts on `PATH` consistently; `uv tool install` provides a clearer isolated CLI installation.
- The existing plugin marketplace is already stored in the repository and can be configured from the GitHub repository source supported by the Codex CLI.

## Decision Log

- 2026-07-23: Use `uv tool install modal-sandbox-sdk` as the primary CLI installation path and keep pip as a documented fallback.
- 2026-07-23: Require CLI 0.4.0+ and schema version 1 without coupling the plugin to an exact package patch release.
- 2026-07-23: Keep installation and upgrades user-authorized; the skill only detects and recommends.

## Outcomes & Retrospective

Plugin 0.2.0 now documents installation from the public GitHub marketplace,
uses an isolated uv tool installation for the published CLI, checks CLI 0.4.0+
before live work, and guides first-time users through a resource-free preview.
Creator, focused, full no-resource, release, and exec-plan checks pass. A fresh
Codex configuration remains the deliberate manual acceptance boundary because
marketplace installation changes user-level Codex state.

## Context and Orientation

- `README.md`
- `plugins/modal-sandbox/`
- `.agents/plugins/marketplace.json`
- `tests/test_plugin_acceptance.py`
- `docs/product-specs/public-plugin-onboarding.md`

## Plan of Work

Publish a remote-install onboarding contract, update the public skill and plugin version, encode representative acceptance scenarios, and validate the plugin without creating Modal resources.

## Concrete Steps

1. Document GitHub marketplace installation and the five-minute first-run path.
2. Add minimum CLI version detection and explicit install/upgrade guidance to the skill.
3. Add deterministic acceptance tests for discovery, lifecycle, persistence, cleanup, and errors.
4. Run creator, package, schema, release, and exec-plan validation.

## Machine State

- `state/feature-list.json`
- `state/session-state.json`
- `state/progress.jsonl`

## Progress

Use `state/progress.jsonl` for detailed checkpoints.

## Testing Approach

Run the official skill and plugin validators, focused packaging and plugin acceptance tests, the full no-resource suite, release readiness, and exec-plan validation. Do not create Modal resources by default.

## Constraints & Considerations

- Keep the SDK/CLI as the execution engine and avoid MCP or bundled Python duplication.
- Preserve explicit user approval for package changes and live Modal operations.
- Treat a fresh Codex configuration test as the final manual acceptance boundary.
