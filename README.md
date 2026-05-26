# Modal Sandbox SDK

Small Python SDK and CLI for creating and working with Modal Sandboxes.

```python
from sandbox import Images, Sandbox

with Sandbox.create(image=Images.PY313) as sb:
    sb.write_text("hello.py", "print('hello from Modal')\n")
    result = sb.run("python hello.py")
    print(result.stdout)
```

The default workspace is `/workspace` inside the Modal sandbox. File helpers use
Modal's native sandbox filesystem APIs, so they do not depend on Python being
available inside custom images.

Raw registry image strings still work when you need a different base image:

```python
from sandbox import Sandbox

with Sandbox.create(image="python:3.12-slim") as sb:
    result = sb.run("python --version")
```

Volumes are opt-in:

```python
from sandbox import Sandbox

with Sandbox.create(workspace_volume="my-workspace") as sb:
    sb.write_text("notes.txt", "persistent content\n")
```

Pass environment variables to the sandbox:

```python
from sandbox import Images, Sandbox

with Sandbox.create(
    image=Images.PY313,
    env={"APP_ENV": "dev"},
) as sb:
    result = sb.run("echo $APP_ENV")
    print(result.stdout)
```

Copy files between your machine and the sandbox:

```python
from sandbox import Images, Sandbox

with Sandbox.create(image=Images.PY313) as sb:
    sb.copy_from_local("input.txt", "input.txt")
    sb.run("cp input.txt output.txt")
    sb.copy_to_local("output.txt", "output.txt")
```

## SDK Methods

The `Sandbox` object exposes a small synchronous API:

```python
sb.run("python hello.py")
sb.write_text("hello.py", "print('hello')\n")
sb.read_text("hello.py")
sb.write_bytes("data.bin", b"hello")
sb.read_bytes("data.bin")
sb.list_files(".")
sb.mkdir("notes")
sb.remove("notes", recursive=True)
sb.copy_from_local("local.txt", "remote.txt")
sb.copy_to_local("remote.txt", "local.txt")
sb.close()
```

Relative paths are resolved inside the sandbox workspace. Absolute paths are
used as-is inside the sandbox.

## CLI

```bash
sandbox --image python:3.13-slim run "python -c 'print(123)'"
```

Commands print JSON for easy inspection.

Each CLI command creates or attaches to a sandbox, performs one operation, and
then closes it. Use a persistent workspace volume when you want file operations
to carry across separate CLI commands:

```bash
sandbox --image python:3.13-slim --workspace-volume my-workspace write game.py --content "print('hello')"
sandbox --image python:3.13-slim --workspace-volume my-workspace read game.py
sandbox --image python:3.13-slim --workspace-volume my-workspace ls .
```

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
