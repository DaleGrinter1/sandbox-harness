# Architecture

`modal-sandbox-sdk` is a small Python SDK and JSON-first CLI for Modal Sandbox command and file workflows.

## Package Boundaries

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
- `sandbox.types`: shared typed configuration and snapshot metadata.

## Design Constraints

- Keep Modal imported lazily so importing `sandbox` stays lightweight.
- Default tests must not create real Modal resources.
- File helpers operate inside the Modal sandbox workspace, never the local repository filesystem.
- CLI output is JSON except `--help` and `--version`.
- Live Modal tests stay opt-in behind `MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1`.

## Validation Commands

```bash
./scripts/dev/check.sh
```
