# Vercel-Style Conveniences

## Summary

The SDK and CLI expose a small Vercel-like sandbox surface while remaining
Modal-first.

## User Goals

- Users can choose runtime aliases such as `python3.13`, `node24`, and `node22`
  instead of writing registry image tags.
- Users can run argv-style commands without shell wrapping.
- Users can start detached command processes for development servers.
- Users can declare sandbox ports and resolve domains for reusable sandboxes.
- Users can write multiple files in one SDK call.

## Behavior

- `runtime` and `image` are mutually exclusive.
- `run_command` and CLI `run-command` pass argv directly to Modal.
- `run_command_detached` returns a `SandboxCommand` handle with logs, wait,
  poll, streams, and return code access.
- Ports must be declared when the sandbox is created.
- CLI `domain` requires `--sandbox-id` so URL lookup happens against a
  reusable sandbox.

## Non-Goals

- No broad provider abstraction beyond Modal.
- No exact parity with Vercel sandbox snapshots or process lifecycle.
- No shell parsing for argv-style commands.

## Examples

```python
from sandbox import Sandbox

with Sandbox.create(runtime="node24", encrypted_ports=[3000]) as sb:
    cmd = sb.run_command_detached("node", ["server.mjs"])
    print(sb.domain(3000))
    cmd.wait()
```

```bash
sandbox --runtime python3.13 run-command python -c "print(123)"
sandbox --runtime node24 --encrypted-port 3000 start
sandbox --sandbox-id sb-abc123 domain 3000
```
