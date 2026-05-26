# Modal Sandbox SDK

Small Python SDK and CLI for creating and working with Modal Sandboxes.

Before your first live sandbox, make sure Modal is installed and authenticated:

```bash
uv run modal setup
```

If that does not work in your environment, try:

```bash
uv run python -m modal setup
```

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

Run a local Python file in a sandbox:

```python
from sandbox import Images, Sandbox

with Sandbox.create(image=Images.PY313) as sb:
    sb.copy_from_local("script.py", "script.py")
    result = sb.run("python script.py")
    print(result.stdout)
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

For agents and automation, start with the discovery commands. They do not create
Modal resources:

```bash
sandbox schema
sandbox doctor
```

`sandbox schema` prints command metadata, output shapes, lifecycle notes, path
rules, auth setup commands, and examples as JSON. `sandbox doctor` reports
whether the Modal Python package is importable and whether credentials appear to
be configured through environment variables or `~/.modal.toml`.

By default, `sandbox run` exits with status `0` when the SDK call succeeds,
even if the command inside the sandbox exits nonzero. Use
`--use-command-exit-code` when shell scripts should receive the sandbox
command's exit status:

```bash
sandbox run --use-command-exit-code "python -c 'raise SystemExit(7)'"
```

Each CLI command creates or attaches to a sandbox, performs one operation, and
then closes it. Use a persistent workspace volume when you want file operations
to carry across separate CLI commands:

```bash
sandbox --image python:3.13-slim --workspace-volume my-workspace write game.py --content "print('hello')"
sandbox --image python:3.13-slim --workspace-volume my-workspace read game.py
sandbox --image python:3.13-slim --workspace-volume my-workspace ls .
sandbox --image python:3.13-slim --workspace-volume my-workspace mkdir notes
sandbox --image python:3.13-slim --workspace-volume my-workspace upload input.txt input.txt
sandbox --image python:3.13-slim --workspace-volume my-workspace run --cwd /workspace "python game.py"
sandbox --image python:3.13-slim --workspace-volume my-workspace download output.txt output.txt
sandbox --image python:3.13-slim --workspace-volume my-workspace rm notes --recursive
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

Live runs require Modal credentials. If you are new to Modal, create/sign in to
your Modal account and run:

```bash
uv run modal setup
```

If your shell cannot find the `modal` command, use:

```bash
uv run python -m modal setup
```

In non-interactive environments such as CI, configure a Modal token instead:

```bash
uv run modal token new
uv run modal token set --token-id <token id> --token-secret <token secret>
```

You can also set `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` in the process
environment. Modal documents the setup flow in its
[getting started guide](https://modal.com/docs/guide) and token options in the
[`modal token` CLI reference](https://modal.com/docs/reference/cli/token).

When Modal reports missing, invalid, or expired credentials, this SDK raises
`ModalAuthenticationError` with the same setup commands so CLI users and Python
callers get a next step instead of a raw Modal traceback.

Unit tests use a fake provider and do not contact Modal.

Live Modal tests are opt-in:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_live.py
```
