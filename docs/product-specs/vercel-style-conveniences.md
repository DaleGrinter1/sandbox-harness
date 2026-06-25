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
- Users can name long-lived sandboxes and reattach by name while they are
  running.
- Users can configure Modal readiness probes and wait until a service is ready.
- Users can write multiple files in one SDK call.

## Behavior

- `runtime` and `image` are mutually exclusive.
- `run_command` and CLI `run-command` pass argv directly to Modal.
- `run_command_detached` returns a `SandboxCommand` handle with logs, wait,
  poll, streams, and return code access.
- Ports must be declared when the sandbox is created.
- Readiness probes are configured when the sandbox is created and can be
  waited on with `wait_until_ready()` or CLI `wait-ready`.
- CLI `domain` requires `--sandbox-id` or `--sandbox-name` so URL lookup
  happens against a reusable sandbox.

## Non-Goals

- No broad provider abstraction beyond Modal.
- No exact parity with Vercel sandbox snapshots or process lifecycle.
- No shell parsing for argv-style commands.

## Examples

```python
from sandbox import Sandbox, SandboxReadinessProbe

with Sandbox.create(
    runtime="node24",
    encrypted_ports=[3000],
    readiness_probe=SandboxReadinessProbe.tcp(3000),
) as sb:
    cmd = sb.run_command_detached("node", ["server.mjs"])
    sb.wait_until_ready(timeout=60)
    print(sb.domain(3000))
    cmd.wait()
```

```bash
sandbox --runtime python3.13 run-command python -c "print(123)"
sandbox --runtime node24 --name agent-workspace --encrypted-port 3000 --readiness-tcp 3000 --wait-ready start
sandbox --sandbox-name agent-workspace wait-ready --timeout 60
sandbox --sandbox-name agent-workspace domain 3000
```
