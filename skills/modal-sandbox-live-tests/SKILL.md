---
name: modal-sandbox-live-tests
description: Opt-in live Modal test workflow guidance for modal-sandbox-sdk. Use when Codex needs to decide whether to run real Modal integration tests, check readiness before live tests, avoid accidental resource creation, run the live test suite, or clean up Modal volumes and sandboxes after testing.
---

# Modal Sandbox Live Tests

Use this skill when a task touches live Modal behavior or the user asks to verify the SDK against real Modal resources.

## Safety Gate

Default tests must not create Modal resources. Before live tests:

1. Run safe readiness checks:

```bash
uv run sandbox doctor
uv run sandbox quickstart
```

2. Confirm the user wants real Modal resources created.
3. Set the opt-in environment variable only for the live test command.

## Live Test Command

Run the live suite explicitly:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_live.py
```

On PowerShell:

```powershell
$env:MODAL_SANDBOX_SDK_RUN_MODAL_TESTS='1'; uv run pytest tests/test_modal_live.py
```

## What The Live Suite Covers

- SDK file helpers inside the sandbox workspace.
- `quickstart --run`.
- CLI file persistence with a workspace volume.
- `start`, `--sandbox-id`, and `stop`.

## Cleanup Expectations

- Ensure long-lived sandboxes are stopped.
- Ensure temporary Modal volumes created by tests are deleted.
- If a live test aborts, inspect the test output for the generated sandbox ID or volume name before retrying.

## Guardrails

- Do not set `MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1` for the full default suite unless the user asked for live validation.
- Do not run live tests when `sandbox doctor` reports missing or partial credentials.
- Prefer the narrow live test file over broad commands when validating provider changes.
