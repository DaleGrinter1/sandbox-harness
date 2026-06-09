---
name: modal-sandbox-file-workflows
description: File workflow guidance for modal-sandbox-sdk. Use when Codex needs to write, read, list, remove, upload, download, or persist files inside Modal Sandbox workspaces using the CLI or Python SDK.
---

# Modal Sandbox File Workflows

Use this skill for sandbox file operations. File helpers operate inside the Modal sandbox workspace, not the local repo, unless explicitly uploading from or downloading to local paths.

## Path Rules

- Relative sandbox paths resolve under `/workspace`.
- Absolute paths are used as absolute paths inside the sandbox.
- Relative paths must not escape the workspace with `..`.

## CLI File Workflow

Use a workspace volume when separate CLI calls should share files:

```bash
uv run sandbox --image py313 --workspace-volume my-workspace write hello.py --content "print('hello')"
uv run sandbox --image py313 --workspace-volume my-workspace run "python hello.py"
uv run sandbox --image py313 --workspace-volume my-workspace read hello.py
```

Use upload/download only when moving files between local disk and the sandbox:

```bash
uv run sandbox --image py313 --workspace-volume my-workspace upload input.txt input.txt
uv run sandbox --image py313 --workspace-volume my-workspace download output.txt output.txt
```

## Persistence Choice

- Use one-shot file commands without a volume only when files do not need to survive the command.
- Use `--workspace-volume` when files should persist across separate sandbox lifetimes.
- Use `sandbox start` and `--sandbox-id` when several operations should share one live sandbox.

## Python SDK File Workflow

```python
from sandbox import Images, Sandbox

with Sandbox.create(image=Images.PY313) as sb:
    sb.write_text("hello.py", "print('hello')\n")
    result = sb.run("python hello.py")
    content = sb.read_text("hello.py")
```

Use `copy_from_local` and `copy_to_local` only for explicit local transfer.
