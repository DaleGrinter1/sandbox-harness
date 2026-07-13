# Modal Sandbox SDK

Small Python SDK and JSON-first CLI for running commands and file workflows
inside Modal Sandboxes. It is a lightweight helper for new users and agents,
not a replacement for Modal's backend or full Python SDK.

Use it when you want to:

- Run a command in a fresh Modal Sandbox.
- Write, read, list, remove, upload, or download sandbox files.
- Keep files across CLI calls with an optional Modal volume.
- Wait for TCP or argv-style readiness probes before issuing work.
- Inspect files, sync a workspace volume, or seed public source after sandbox
  creation.
- Inspect a JSON-friendly CLI contract before creating Modal resources.

## Quick Start

Install the package (requires Python 3.11+):

```bash
pip install modal-sandbox-sdk
```

Check your local Modal setup without creating resources:

```bash
sandbox dry
sandbox doctor
sandbox quickstart
```

For repository development, install dependencies with `uv`:

```bash
uv sync
```

Inspect the CLI contract without creating Modal resources:

```bash
uv run sandbox dry
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

Optional agent context from Modal itself is available through Modal SDK 1.5's
skills CLI:

```bash
uv run modal skills show
uv run modal skills install --yes
```

This installs Modal's upstream agent skill for general Modal guidance. The
repo-local `modal-sandbox-*` skills remain development helpers for this package.

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

Dry commands / safe discovery, no Modal resources:

```bash
uv run sandbox dry
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
uv run sandbox --image py313 --workspace-volume work sync
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

Use a readiness probe when a sandbox service should be healthy before follow-up
commands or port lookups run:

```python
from sandbox import Sandbox, SandboxReadinessProbe

with Sandbox.create(
    runtime="node24",
    encrypted_ports=[3000],
    readiness_probe=SandboxReadinessProbe.tcp(3000),
) as sb:
    sb.wait_until_ready(timeout=60)
    print(sb.domain(3000))
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

Restrict sandbox network access when running agentic or CI workflows that
should not reach arbitrary hosts:

```python
with Sandbox.create(
    image=Images.PY313,
    outbound_domain_allowlist=["api.openai.com", "github.com"],
    outbound_cidr_allowlist=["10.0.0.0/8"],
    inbound_cidr_allowlist=["203.0.113.0/24"],
) as sb:
    print(sb.run("python -c 'print(123)'").stdout)
```

The same volume primitive is available from its focused module:

```python
from sandbox.volumes import SandboxVolume
```

For Vercel-style Python SDK workflows, use runtime aliases, argv commands,
detached command handles, declared ports, bulk file writes, and volume-backed
workspace checkpoints:

```python
with Sandbox.create(runtime="python3.13", encrypted_ports=[3000]) as sb:
    result = sb.run_command("python", ["-c", "print(123)"])
    print(result.stdout)
```

See [docs/design-docs/vercel-style-sdk-compatibility.md](docs/design-docs/vercel-style-sdk-compatibility.md) for details and limitations.

Workspace checkpoints and Modal-native image snapshots are separate APIs.
`workspace_checkpoint()` and its compatibility alias `create_snapshot()` return
metadata for the Modal volume mounted at the workspace. `snapshot_filesystem()`
and `snapshot_directory()` return JSON-friendly Modal image snapshot metadata.

```python
from sandbox import Sandbox, SandboxVolume

with Sandbox.create(runtime="python3.13", volumes=[SandboxVolume.workspace("work")]) as sb:
    sb.write_text("app.py", "print(123)\n")
    checkpoint = sb.workspace_checkpoint()
    file_info = sb.stat("app.py")
    print(checkpoint.to_dict(), file_info.to_dict())

with Sandbox.create(runtime="python3.13") as sb:
    image_snapshot = sb.snapshot_directory(".", ttl=7 * 24 * 3600)
    sb.mount_image("restored", image_snapshot)
```

The `Sandbox` object exposes a small synchronous API:

```python
Sandbox.create(...)
Sandbox.from_id(...)
Sandbox.from_name(...)
Sandbox.get_or_create(...)
Sandbox.from_snapshot(...)
Sandbox.from_provider(...)
SandboxReadinessProbe.tcp(3000)
SandboxReadinessProbe.exec(["python", "-c", "raise SystemExit(0)"])
sb.config
sb.sandbox_id
sb.wait_until_ready(timeout=300)
sb.run("python hello.py")
sb.run_command("python", ["-c", "print('hello')"])
sb.run_command_detached("npm", ["run", "dev"])
sb.write_text("hello.py", "print('hello')\n")
sb.read_text("hello.py")
sb.write_bytes("data.bin", b"hello")
sb.read_bytes("data.bin")
sb.write_files([{"path": "hello.py", "content": "print('hello')\n", "mode": 0o644}])
sb.list_files(".")
sb.mkdir("notes")
sb.remove("notes", recursive=True)
sb.copy_from_local("local.txt", "remote.txt")
sb.copy_to_local("remote.txt", "local.txt")
sb.domain(3000)
sb.workspace_checkpoint()
sb.create_snapshot()
sb.snapshot_filesystem(timeout=55, ttl=30 * 24 * 3600)
sb.snapshot_directory(".", timeout=55, ttl=30 * 24 * 3600)
sb.mount_image("snapshots/app", "im-abc123")
sb.unmount_image("snapshots/app")
sb.stat("hello.py")
list(sb.watch(".", recursive=True, timeout=5))
sb.sync_workspace()
sb.seed_git("https://github.com/example/project.git", destination="src")
sb.seed_tarball("https://example.com/source.tar.gz", destination="src")
sb.detach()
sb.terminate()
sb.close()
```

## CLI

The CLI command is `sandbox`. Commands print JSON except for `--help` and
`--version`. Failures also print a JSON error envelope to stderr.

Discovery commands do not create Modal resources:

```bash
uv run sandbox dry
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

Restrict sandbox network access:

```bash
uv run sandbox --allow-domain api.openai.com --allow-domain github.com run "python app.py"
uv run sandbox --allow-cidr 10.0.0.0/8 run "python app.py"
uv run sandbox --encrypted-port 8080 --allow-inbound-cidr 203.0.113.0/24 start
```

Create a reusable sandbox for a longer workflow:

```bash
uv run sandbox --image py313 --name agent-workspace start
uv run sandbox --sandbox-name agent-workspace write hello.py --content "print('hello')"
uv run sandbox --sandbox-name agent-workspace run "python hello.py"
uv run sandbox --sandbox-name agent-workspace stop
```

Wait for service readiness when creating or reusing a sandbox:

```bash
uv run sandbox --runtime node24 --encrypted-port 3000 --readiness-tcp 3000 --wait-ready start
uv run sandbox --sandbox-id sb-abc123 wait-ready --timeout 60
uv run sandbox --readiness-exec "python -c 'import pathlib; raise SystemExit(not pathlib.Path(\"/tmp/ready\").exists())'" --wait-ready run "python app.py"
```

Inspect files, sync a workspace volume, and seed public source:

```bash
uv run sandbox --workspace-volume work stat app.py
uv run sandbox --workspace-volume work watch . --timeout 5 --recursive
uv run sandbox --workspace-volume work sync
uv run sandbox --workspace-volume work seed-git https://github.com/example/project.git --dest src
uv run sandbox --workspace-volume work seed-tarball https://example.com/source.tar.gz --dest src
```

Modal-native image snapshots are explicit commands. They return image metadata,
not volume checkpoint metadata:

```bash
uv run sandbox snapshot-filesystem --ttl 604800
uv run sandbox snapshot-directory . --ttl 604800
uv run sandbox --sandbox-id sb-abc123 mount-image restored im-abc123
uv run sandbox --sandbox-id sb-abc123 unmount-image restored
```

Private source workflows should use Modal secrets, a custom Modal image, or a
caller-provided setup command inside the sandbox. The CLI intentionally has no
token-taking source flags.

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
Commands such as `snapshot` and `domain` validate their required lifecycle
flags before creating Modal resources.

## Examples

Small examples live in `examples/`:

- `examples/run_python.py`: create a sandbox, write a Python file, and run it.
- `examples/argv_command.py`: run an argv-style command without shell wrapping.
- `examples/volume_mounts.py`: mount workspace and cache volumes.
- `examples/reuse_sandbox.py`: create one sandbox and detach it for reuse.
- `examples/node_dev_server.py`: expose a small Node server through a port.
- `examples/openai_agent_loop.py`: prompt a tiny OpenAI Responses API loop.
- `examples/cli_file_workflow.sh`: write, run, and read a file with the CLI.
- `examples/persistent_volume.sh`: keep files across sandbox lifetimes with a
  Modal volume.

## More Docs

- [CLI workflows](docs/references/cli.md)
- [New agent starter prompt](docs/references/new-agent-prompt.md)
- [Cognitive-load design note](docs/design-docs/cognitive-load.md)
- [Vercel-style SDK compatibility](docs/design-docs/vercel-style-sdk-compatibility.md)
- [Collaborator onboarding](docs/references/collaborator-onboarding.md)
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
uv run sandbox dry
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
```

Commands such as `quickstart --run`, `start`, `stop`, `run`, `run-command`,
`write`, `read`, `ls`, `mkdir`, `rm`, `upload`, `download`, `domain`,
`snapshot`, `snapshot-filesystem`, `snapshot-directory`, `mount-image`,
`unmount-image`, `stat`, `watch`, `sync`, `wait-ready`, `seed-git`, and
`seed-tarball` contact Modal.

**My file disappeared after a command.**

One-shot sandboxes are terminated when the command finishes. Use
`--workspace-volume my-workspace` when separate CLI calls should share files,
or use `sandbox start` plus `--sandbox-id` for one live workflow.
