---
name: modal-sandbox-provider-adapter
description: Modal provider adapter guidance for modal-sandbox-sdk. Use when Codex changes provider_modal.py, Sandbox provider behavior, path resolution, Modal auth/provider error handling, lifecycle attach/create/close semantics, image or volume resolution, or fake-provider test coverage.
---

# Modal Sandbox Provider Adapter

Use this skill when touching `packages/sandbox/provider_modal.py` or the provider-facing parts of `Sandbox`.

## Design Constraints

- Keep Modal imported lazily so package import stays lightweight.
- Preserve fake-provider testability through the `SandboxProvider` protocol.
- Keep file helpers operating inside the Modal sandbox workspace, not the local repo.
- Keep default tests free of real Modal resources.

## Path And Filesystem Rules

- Use `sandbox_path(...)` for SDK file helper paths.
- Relative paths resolve under the configured workspace.
- Absolute paths remain absolute sandbox paths.
- Relative paths must not escape the workspace with `..`.

## Error Handling

- Translate Modal auth errors into `ModalAuthenticationError` with setup guidance.
- Wrap unexpected provider failures in `SandboxProviderError`.
- Nonzero command exits should remain `CommandResult` values, not exceptions.
- Add operation context to new errors when it helps users debug without exposing noisy Modal internals.

## Lifecycle Rules

- Created providers own their sandbox and terminate on `close()`.
- Attached providers do not own the sandbox and detach on `close()`.
- `stop`-style flows may attach with `ensure_workspace=False`.
- Prefer explicit `detach()` or `terminate()` when changing lifecycle behavior.

## Validation

Run provider-focused tests after changes:

```bash
uv run pytest tests/test_provider_modal.py tests/test_sandbox.py
```

Run live Modal tests only with explicit opt-in when provider behavior needs real verification.
