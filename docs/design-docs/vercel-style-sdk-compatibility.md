# Vercel-Style SDK Compatibility

This SDK keeps its existing Modal-first API and adds a small Vercel-like Python
surface for teams that want familiar sandbox workflows on Modal.

Existing methods still work:

```python
from sandbox import Sandbox

with Sandbox.create(image="python:3.13-slim") as sb:
    result = sb.run("python -c 'print(123)'")
    print(result.stdout)
```

## Runtime Aliases

Use Vercel-style runtime names when you do not need a custom Modal image:

```python
with Sandbox.create(runtime="python3.13") as sb:
    print(sb.run_command("python", ["--version"]).stdout)
```

Supported aliases:

- `python3.13` -> `python:3.13-slim`
- `node24` -> `node:24-slim`
- `node22` -> `node:22-slim`

Pass either `runtime` or `image`, not both.

The CLI exposes the same aliases:

```bash
uv run sandbox --runtime python3.13 run-command python --version
```

## Argv Commands

`run_command` runs commands without shell wrapping:

```python
with Sandbox.create(runtime="python3.13") as sb:
    result = sb.run_command("python", ["-c", "print(123)"])
    print(result.exit_code)
```

Use `run` when you intentionally want shell syntax such as pipes, redirects, or
inline environment expansion.

## Detached Commands

Start a command and keep a process-style handle:

```python
with Sandbox.create(runtime="node24") as sb:
    cmd = sb.run_command_detached("npm", ["run", "dev"])
    for line in cmd.logs():
        print(line, end="")
    print(cmd.poll())
```

The handle exposes `logs()`, `wait()`, `poll()`, `returncode`, `stdout`, and
`stderr`.

## Files

Write multiple files in one SDK call:

```python
from sandbox import SandboxFile, SandboxVolume

with Sandbox.create(runtime="python3.13") as sb:
    sb.write_files([
        SandboxFile(path="main.py", content="print('hello')\n"),
        {"path": "data.bin", "content": b"data"},
    ])
```

## Ports

Declare ports when creating the sandbox, then ask for the public domain:

```python
with Sandbox.create(runtime="node24", encrypted_ports=[3000]) as sb:
    sb.run_command_detached("npm", ["run", "dev"])
    print(sb.domain(3000))
```

Ports are backed by Modal tunnels. A port must be declared at creation time.

For CLI workflows, declare the port when the sandbox is started and then attach
to retrieve the domain:

```bash
uv run sandbox --runtime node24 --encrypted-port 3000 start
uv run sandbox --sandbox-id sb-abc123 domain 3000
```

## Volume-Backed Snapshots

`create_snapshot` and `from_snapshot` provide a Vercel-like workflow using Modal
volumes:

```python
with Sandbox.create(runtime="python3.13", volumes=[SandboxVolume.workspace("my-workspace")]) as sb:
    sb.write_text("notes.txt", "saved in the workspace\n")
    snapshot = sb.create_snapshot()

with Sandbox.from_snapshot(snapshot.name, runtime="python3.13") as sb:
    print(sb.read_text("notes.txt"))
```

For ordinary SDK creation, prefer first-class volume mounts when you want to
name the volume and mount path together:

```python
with Sandbox.create(
    runtime="python3.13",
    volumes=[
        SandboxVolume.workspace("my-workspace"),
        SandboxVolume(volume="cache-volume", mount_path="/cache"),
    ],
) as sb:
    sb.write_text("notes.txt", "saved in the workspace\n")
```

These snapshots preserve workspace files through a Modal volume. They are not
full Vercel snapshots: they do not capture installed system packages, running
processes, or the full VM filesystem.
The SDK reports the mounted workspace volume as the checkpoint and does not use
Modal's local `Volume.commit()` API, which is only valid for mounted volumes
inside a container.

The CLI command is the same volume-backed checkpoint:

```bash
uv run sandbox --workspace-volume my-workspace snapshot
```
