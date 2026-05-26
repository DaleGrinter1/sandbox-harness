# Modal Sandbox SDK

Small Python SDK and CLI for creating and working with Modal Sandboxes.

```python
from sandbox import Sandbox

with Sandbox.create(image="python:3.13-slim") as sb:
    sb.write_text("hello.py", "print('hello from Modal')\n")
    result = sb.run("python hello.py")
    print(result.stdout)
```

The default workspace is `/workspace` inside the Modal sandbox. File helpers use
Modal's native sandbox filesystem APIs, so they do not depend on Python being
available inside custom images.

Volumes are opt-in:

```python
from sandbox import Sandbox

with Sandbox.create(workspace_volume="my-workspace") as sb:
    sb.write_text("notes.txt", "persistent content\n")
```

## CLI

```bash
sandbox run "python -c 'print(123)'"
sandbox write game.py --content "print('hello')"
sandbox read game.py
sandbox ls .
```

Commands print JSON for easy inspection.

## Development

This repo uses `uv` for dependency management and local commands.

```bash
uv sync
uv run pytest
uv run sandbox --help
uv run sandbox run "python -c 'print(123)'"
```

## Modal Setup

Live runs require Modal credentials configured in your environment. Unit tests
use a fake provider and do not contact Modal.

Live Modal tests are opt-in:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_live.py
```
