# Reliability

## Guarantees

- Default tests do not create real Modal resources.
- Nonzero sandbox command exits are returned as `CommandResult.exit_code`, not raised.
- CLI runtime and argument failures use JSON error envelopes.
- Attached sandboxes detach on close; created sandboxes terminate on close.
- `sandbox schema` exposes golden workflows for safe discovery, short-lived
  execution, persistent workspace files, and long-lived reuse.
- Snapshot commands require a workspace volume and report a JSON runtime error
  when no persistent workspace volume is configured.
- Provider failures include operation context such as sandbox creation,
  attach, command execution, filesystem operation, or tunnel resolution.

## Validation

```bash
./scripts/dev/check.sh
```

Live Modal validation is opt-in:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 ./scripts/dev/live-smoke.sh
```

The default fake-provider tests verify CLI shape, lifecycle routing, volume
translation, path rules, and error envelopes. The opt-in live suite verifies
the Modal boundary: SDK file helpers, `quickstart --run`, persisted CLI files
with `--workspace-volume`, `snapshot`, declared-port `domain`, and
`start`/`--sandbox-id`/`stop`.
