---
name: modal-sandbox-python-sdk
description: Python SDK guidance for modal-sandbox-sdk. Use when Codex needs to write Python code using the sandbox package, create Modal Sandboxes, run commands, inspect CommandResult objects, use Images presets, manage lifecycle, or perform file operations through the SDK.
---

# Modal Sandbox Python SDK

Use the public package `sandbox` for Python workflows. Keep examples small and synchronous.

## Basic Pattern

```python
from sandbox import Images, Sandbox

with Sandbox.create(image=Images.PY313) as sb:
    sb.write_text("hello.py", "print('hello from Modal')\n")
    result = sb.run("python hello.py")
    print(result.stdout)
```

Prefer context managers so sandboxes close cleanly.

## Command Results

`sb.run(...)` returns a `CommandResult` with:

- `stdout`
- `stderr`
- `exit_code`
- `duration_ms`
- `timed_out`

Nonzero command exits are represented in `exit_code`; they are not raised as Python exceptions by default.

## Files And Paths

- Relative paths resolve inside the sandbox workspace, normally `/workspace`.
- Use `write_text`, `read_text`, `write_bytes`, `read_bytes`, `list_files`, `mkdir`, and `remove` for sandbox files.
- Use `copy_from_local` and `copy_to_local` only when local filesystem transfer is intended.
- Use `workspace_volume` when files should persist after a sandbox closes.

## Creation Options

Use `Images.PY313` for beginner Python examples. Use raw registry image strings only when the user needs a specific image.

Pass `env`, `cpu`, `memory`, `gpu`, `region`, `block_network`, `command_timeout`, and `sandbox_timeout` only when the task needs them.

## Setup And Safety

If the user is unsure whether Modal is configured, prefer the CLI readiness check:

```bash
uv run sandbox doctor
```

Live Modal tests and real resources are opt-in. Do not create live sandboxes unless the user has asked for execution.
