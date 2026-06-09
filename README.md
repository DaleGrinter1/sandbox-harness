# Modal Sandbox SDK

Small Python SDK and CLI for running commands and file workflows inside Modal
Sandboxes.

Use it when you want to:

- Run a command in a fresh Modal Sandbox.
- Write, read, list, remove, upload, or download sandbox files.
- Keep files across CLI calls with an optional Modal volume.
- Inspect a JSON-friendly CLI contract before creating Modal resources.

## Quick Start

Install the package:

```bash
pip install modal-sandbox-sdk
```

Check your local Modal setup without creating resources:

```bash
sandbox doctor
sandbox quickstart
```

For repository development, install dependencies with `uv`:

```bash
uv sync
```

Inspect the CLI contract without creating Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
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

## Golden Paths

These are the workflows this repo optimizes for and regression-tests.

Safe discovery, no Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
```

Short-lived execution:

```bash
uv run sandbox --image py313 quickstart --run
uv run sandbox --image py313 run "python -c 'print(123)'"
```

Persistent files across separate sandbox lifetimes:

```bash
uv run sandbox --image py313 --workspace-volume work write app.py --content "print(123)"
uv run sandbox --image py313 --workspace-volume work run "python app.py"
uv run sandbox --image py313 --workspace-volume work read app.py
uv run sandbox --image py313 --workspace-volume work snapshot
```

Reusable long-lived sandbox:

```bash
uv run sandbox --image py313 start
uv run sandbox --sandbox-id sb-abc123 write app.py --content "print(123)"
uv run sandbox --sandbox-id sb-abc123 run "python app.py"
uv run sandbox stop sb-abc123
```

Agents can also read these workflows from `uv run sandbox schema` under
`golden_workflows`.

## Python SDK

The public package is `sandbox`.

```python
from sandbox import Images, Sandbox, SandboxVolume

with Sandbox.create(
    image=Images.PY313,
    volumes=[SandboxVolume.workspace("my-workspace")],
) as sb:
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

Use registry image strings, environment variables, output caps, and first-class
volume mounts when a workflow needs them:

```python
with Sandbox.create(
    image="python:3.12-slim",
    env={"APP_ENV": "dev"},
    volumes=[
        SandboxVolume.workspace("my-workspace"),
        SandboxVolume(volume="cache-volume", mount_path="/cache"),
    ],
    max_output_bytes=1024 * 1024,
) as sb:
    print(sb.run("python --version").stdout)
```

The same volume primitive is available from its focused module:

```python
from sandbox.volumes import SandboxVolume
```

For Vercel-style Python SDK workflows, use runtime aliases, argv commands,
detached command handles, declared ports, bulk file writes, and volume-backed
snapshots:

```python
with Sandbox.create(runtime="python3.13", encrypted_ports=[3000]) as sb:
    result = sb.run_command("python", ["-c", "print(123)"])
    print(result.stdout)
```

See [docs/design-docs/vercel-style-sdk-compatibility.md](docs/design-docs/vercel-style-sdk-compatibility.md) for details and limitations.

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

Discovery commands do not create Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
```

Run a command:

```bash
uv run sandbox --image py313 run "python -c 'print(123)'"
```

Run a command without shell parsing:

```bash
uv run sandbox --runtime python3.13 run-command python -c "print(123)"
```

Mount an additional Modal volume:

```bash
uv run sandbox --volume cache-volume:/cache run "ls /cache"
```

Create a reusable sandbox for a longer workflow:

```bash
uv run sandbox --image py313 start
uv run sandbox --sandbox-id sb-abc123 write hello.py --content "print('hello')"
uv run sandbox --sandbox-id sb-abc123 run "python hello.py"
uv run sandbox stop sb-abc123
```

The CLI accepts registry tags such as `python:3.13-slim`, beginner image aliases
such as `py313`, `py312`, `py311`, and `ubuntu24`, and runtime aliases such as
`python3.13`, `node24`, and `node22`.

See [docs/references/cli.md](docs/references/cli.md) for full CLI workflows.

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
- `examples/argv_command.py`: run an argv-style command without shell wrapping.
- `examples/volume_mounts.py`: mount workspace and cache volumes.
- `examples/reuse_sandbox.py`: create one sandbox and detach it for reuse.
- `examples/node_dev_server.py`: expose a small Node server through a port.
- `examples/cli_file_workflow.sh`: write, run, and read a file with the CLI.
- `examples/persistent_volume.sh`: keep files across sandbox lifetimes with a
  Modal volume.

## More Docs

- [CLI workflows](docs/references/cli.md)
- [Vercel-style SDK compatibility](docs/design-docs/vercel-style-sdk-compatibility.md)
- [Modal setup](docs/references/modal-setup.md)
- [Development](docs/references/development.md)
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
uv run sandbox quickstart
```

Commands such as `quickstart --run`, `run`, `write`, `read`, `ls`, `upload`,
`download`, `start`, and `stop` contact Modal.

**My file disappeared after a command.**

One-shot sandboxes are terminated when the command finishes. Use
`--workspace-volume my-workspace` when separate CLI calls should share files,
or use `sandbox start` plus `--sandbox-id` for one live workflow.
