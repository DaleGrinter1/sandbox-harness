# Modal Sandbox SDK

Small Python SDK and CLI for running commands and file workflows inside Modal
Sandboxes.

Use it when you want to:

- Run a command in a fresh Modal Sandbox.
- Write, read, list, remove, upload, or download sandbox files.
- Keep files across CLI calls with an optional Modal volume.
- Give agents a JSON-friendly CLI they can inspect before they act.

## Quick Start

Install dependencies for this repo:

```bash
uv sync
```

Inspect the CLI contract without creating Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox recipes
uv run sandbox quickstart
```

If `doctor` reports missing credentials, sign in to Modal:

```bash
uv run modal setup
```

If your shell cannot find the `modal` command, use:

```bash
uv run python -m modal setup
```

Run the beginner quickstart in a short-lived Modal Sandbox:

```bash
uv run sandbox --image py313 quickstart --run
```

Then run any command:

```bash
uv run sandbox --image py313 run "python -c 'print(123)'"
```

## Python SDK

The public package is `sandbox`.

```python
from sandbox import Images, Sandbox

with Sandbox.create(image=Images.PY313) as sb:
    sb.write_text("hello.py", "print('hello from Modal')\n")
    result = sb.run("python hello.py")
    print(result.stdout)
```

Relative paths are resolved inside the sandbox workspace, which defaults to
`/workspace`:

```python
with Sandbox.create(image=Images.PY313) as sb:
    sb.write_text("notes/todo.txt", "ship it\n")
    print(sb.read_text("notes/todo.txt"))
```

Use registry image strings, environment variables, output caps, and persistent
workspace volumes when a workflow needs them:

```python
with Sandbox.create(
    image="python:3.12-slim",
    env={"APP_ENV": "dev"},
    workspace_volume="my-workspace",
    max_output_bytes=1024 * 1024,
) as sb:
    print(sb.run("python --version").stdout)
```

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

## CLI

The CLI command is `sandbox`. Commands print JSON except for `--help` and
`--version`. Failures also print a JSON error envelope to stderr.

Agent-friendly discovery commands do not create Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox recipes
uv run sandbox quickstart
```

Run a command:

```bash
uv run sandbox --image py313 run "python -c 'print(123)'"
```

Create a reusable sandbox for a longer workflow:

```bash
uv run sandbox --image py313 start
uv run sandbox --sandbox-id sb-abc123 write hello.py --content "print('hello')"
uv run sandbox --sandbox-id sb-abc123 run "python hello.py"
uv run sandbox stop sb-abc123
```

The CLI accepts registry tags such as `python:3.13-slim` and beginner aliases
such as `py313`, `py312`, `py311`, and `ubuntu24`.

See [docs/cli.md](docs/cli.md) for full CLI workflows.

## Paths And Lifecycle

Relative paths are resolved inside the sandbox workspace. Absolute paths are
used as-is inside the sandbox. Relative paths cannot use `..` to escape the
workspace.

Each CLI command creates or attaches to a sandbox, performs one operation, and
then closes it. Created one-shot sandboxes are terminated on close. Sandboxes
attached with `--sandbox-id` are detached on close and keep running.

Use `start` when separate CLI calls should share one live sandbox. Use
`--workspace-volume` when separate sandbox lifetimes need to share files.

## Examples

Small examples live in `examples/`:

- `examples/run_python.py`: create a sandbox, write a Python file, and run it.
- `examples/cli_file_workflow.sh`: write, run, and read a file with the CLI.
- `examples/persistent_volume.sh`: keep files across sandbox lifetimes with a
  Modal volume.

The same workflow ideas are available as JSON:

```bash
uv run sandbox recipes
```

## More Docs

- [CLI workflows](docs/cli.md)
- [Modal setup](docs/modal-setup.md)
- [Agent and MCP notes](docs/agents.md)
- [Development](docs/development.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Common Problems

**Modal credentials are missing.**

Run:

```bash
uv run sandbox doctor
uv run modal setup
```

For CI or other non-interactive environments, use `uv run modal token new` and
then configure `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`.

**I do not know which commands create Modal resources.**

Safe discovery commands are:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox recipes
uv run sandbox quickstart
```

Commands such as `quickstart --run`, `run`, `write`, `read`, `ls`, `upload`,
`download`, `start`, and `stop` contact Modal.

**My file disappeared after a command.**

One-shot sandboxes are terminated when the command finishes. Use
`--workspace-volume my-workspace` when separate CLI calls should share files,
or use `sandbox start` plus `--sandbox-id` for one live workflow.
