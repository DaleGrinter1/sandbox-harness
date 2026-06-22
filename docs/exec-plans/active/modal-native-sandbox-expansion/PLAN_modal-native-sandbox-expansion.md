# PLAN_modal-native-sandbox-expansion

## Purpose / Big Picture

Expand `modal-sandbox-sdk` with a small set of Modal-native Sandbox features while keeping the package lightweight, compatibility-safe, and useful through both the Python SDK and JSON-first CLI.

The work starts with low-risk hardening: local network-policy validation, executable file modes in bulk writes, and idempotent close behavior. Later phases add named sandboxes, clearer snapshot APIs, filesystem inspection, and explicit source seeding without turning the package into a generic sandbox abstraction.

## Surprises & Discoveries

- Modal's current Sandbox API already supports named sandboxes, tags, CIDR allowlists, `idle_timeout`, `h2_ports`, OIDC identity tokens, readiness probes, filesystem/directory snapshots, image mounts, connect tokens, and filesystem stat/watch helpers.
- The existing `create_snapshot()` method intentionally returns volume-backed metadata, not a Modal filesystem image snapshot. Keep this behavior as compatibility surface and add clearer names beside it.
- Relative command `cwd` handling and detached command timeouts were fixed before this initiative was created; keep those edits intact while continuing the larger review work.

## Decision Log

- 2026-06-21: Use a multi-phase active initiative because the review items touch public SDK API, provider behavior, CLI schema, docs, and live Modal validation.
- 2026-06-21: Implement Phase 1 first. It provides immediate safety and ergonomics without forcing early decisions about snapshot return types or source-seeding credentials.
- 2026-06-21: Keep Modal imported lazily and keep default validation resource-free. Live Modal tests remain opt-in.

## Outcomes & Retrospective

Pending. Summarize shipped API changes, validation evidence, and deferred follow-up once the initiative completes.

## Context and Orientation

Read these first:

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/PLANS.md`
- `docs/design-docs/core-beliefs.md`
- `docs/design-docs/vercel-style-sdk-compatibility.md`
- `docs/product-specs/index.md`
- `docs/product-specs/sandbox-domain-allowlist.md`
- `docs/product-specs/vercel-style-conveniences.md`
- `docs/product-specs/volume-backed-snapshots.md`
- `packages/sandbox/sandbox.py`
- `packages/sandbox/provider_modal.py`
- `packages/sandbox/types.py`
- `packages/sandbox/files.py`
- `packages/sandbox_cli/cli.py`
- `tests/test_sandbox.py`
- `tests/test_provider_modal.py`
- `tests/test_cli.py`

Relevant Modal docs are also bundled under `.agents/skills/modal/references/`, especially:

- `api/modal.Sandbox.md`
- `guide/sandbox-networking.md`
- `guide/sandbox-snapshots.md`
- `guide/sandbox-files.md`
- `guide/sandboxes.md`

## Plan of Work

Phase 1 hardens existing surfaces. Add CIDR allowlists and stricter allowlist validation, reject incompatible network policy combinations locally, support file modes in `SandboxFile`, and make provider close behavior idempotent.

Phase 2 adds Modal-native lifecycle ergonomics: named sandboxes, tags, `from_name`, and eventually `get_or_create` with precise not-found handling. Include high-value Modal creation options only when they can be passed through without compromising lazy imports.

Phase 3 clarifies snapshot semantics. Add `workspace_checkpoint()` for the current volume-backed behavior, keep `create_snapshot()` as a compatibility alias, and add Modal-native filesystem/directory snapshot and image mount helpers.

Phase 4 adds filesystem inspection and volume sync helpers: `stat()`, `watch()`, and `sync_workspace()`.

Phase 5 adds explicit source seeding after sandbox creation. Use argv-style commands, redact credentials, and require Modal secrets rather than repository token examples for private sources.

Phase 6 updates packaging and CI once the surface settles, including a possible Modal `<2` upper bound and a Python 3.11/3.12/3.13 CI matrix.

## Concrete Steps

1. Scaffold this active initiative and state files.
2. Add SDK config fields for outbound/inbound CIDR allowlists and local validation helpers.
3. Update Modal provider creation kwargs for the new network policy fields.
4. Add CLI flags and schema/docs for CIDR allowlists.
5. Add `SandboxFile.mode` and apply file modes through argv-style `chmod` after writes.
6. Make `ModalSandboxProvider.close()` idempotent for owned and attached sandboxes.
7. Add fake-provider and CLI tests for the Phase 1 behavior.
8. Regenerate `docs/generated/cli-schema.json`.
9. Run focused tests, exec-plan validation, and `./scripts/dev/check.sh` before marking Phase 1 passing.

## Machine State

Implementation state is stored beside this plan:

- `state/feature-list.json` is the canonical implementation checklist.
- Every feature starts with `"passes": false`.
- `state/session-state.json` tracks the active feature, blockers, next action, and handoff rules.
- `state/progress.jsonl` is append-only and records meaningful checkpoints with structured evidence.

Do not create markdown task files or `tasks/` directories for default execution tracking.

## Progress

See `state/progress.jsonl` for detailed checkpoints.

## Testing Approach

Default validation must not create real Modal resources.

Use focused checks while implementing:

```bash
uv run pytest tests/test_sandbox.py tests/test_provider_modal.py
uv run pytest tests/test_cli.py
./scripts/execplan/check.sh
```

Before marking a feature passing, run:

```bash
./scripts/dev/check.sh
```

Live Modal tests remain opt-in only:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 ./scripts/dev/live-smoke.sh
```

## Constraints & Considerations

- Keep Modal imported lazily.
- Do not create real Modal resources in default tests.
- CLI schema, parser behavior, docs, and tests move together.
- Preserve `create_snapshot()` compatibility until a deliberate breaking release.
- Avoid shell interpolation for new command helpers that accept user-controlled paths or credentials.
- Do not add token-looking placeholders or example Modal credentials.
