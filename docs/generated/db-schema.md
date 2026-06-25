# Generated Schema

This repository does not use a database. The closest typed schema source is the Python SDK data model:

- `packages/sandbox/types.py`
- `packages/sandbox/commands.py`
- `packages/sandbox/files.py`
- `packages/sandbox/volumes.py`

## Current Typed Structures

- `SandboxConfig`: sandbox creation and attachment configuration.
- `CommandResult`: command result JSON shape.
- `SandboxCommand`: detached process wrapper.
- `SandboxFile`: bulk file write input.
- `SandboxVolume`: Modal volume mount declaration.
- `SandboxSnapshot`: volume-backed snapshot metadata.
- `SandboxImageSnapshot`: Modal image snapshot metadata.
- `SandboxFileStat`: sandbox file metadata returned by `stat`.
- `SandboxWatchEvent`: bounded sandbox filesystem watch event.
- `SandboxReadinessProbe`: JSON-friendly Modal readiness probe specification.

## Regeneration Method

Update this file whenever public dataclasses or JSON payload shapes change:

```bash
uv run pytest tests/test_packaging.py tests/test_cli.py
uv run sandbox schema
```
