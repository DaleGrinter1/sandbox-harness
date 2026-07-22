# Architecture

The `modal-sandbox` Codex plugin is the primary product entry point for coding agents. It delegates execution to the public `modal-sandbox-sdk` package and its JSON-first `sandbox` CLI; the plugin does not duplicate the Python implementation or add an MCP server.

## Package Boundaries

- `plugins/modal-sandbox/`: distributable Codex plugin and end-user skill.
- `.agents/plugins/marketplace.json`: repo-local plugin marketplace entry.
- `packages/sandbox/`: public Python SDK.
- `packages/sandbox_cli/`: CLI entrypoint and JSON contract.
- `tests/`: fake-provider unit tests plus opt-in live Modal tests.
- `examples/`: small runnable examples for installed users.
- `docs/`: repository knowledge system and user-facing workflow docs.

## SDK Modules

- `sandbox.sandbox`: high-level `Sandbox` facade.
- `sandbox.provider_modal`: Modal adapter and path translation.
- `sandbox.commands`: command results and detached command handles.
- `sandbox.files`: file write primitives.
- `sandbox.volumes`: first-class volume mount primitives.
- `sandbox.errors`: package-specific exceptions.
- `sandbox.types`: shared typed configuration, readiness, and snapshot metadata.

## Design Constraints

- Require an installed `sandbox` CLI and discover capabilities through `sandbox schema --agent`.
- Keep plugin discovery resource-free and require explicit authorization for live Modal operations.
- Keep Modal imported lazily so importing `sandbox` stays lightweight.
- Default tests must not create real Modal resources.
- File helpers operate inside the Modal sandbox workspace, never the local repository filesystem.
- CLI output is JSON except `--help` and `--version`.
- Live Modal tests stay opt-in behind `MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1`.

## Validation Commands

```bash
./scripts/dev/check.sh
```
