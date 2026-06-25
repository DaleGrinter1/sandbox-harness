# Reliability

## Guarantees

- Default tests do not create real Modal resources.
- Nonzero sandbox command exits are returned as `CommandResult.exit_code`, not raised.
- CLI runtime and argument failures use JSON error envelopes.
- Attached sandboxes detach on close; created sandboxes terminate on close.
- `sandbox dry` and `sandbox --dry` expose safe discovery metadata without
  creating Modal resources.
- `sandbox schema` exposes golden workflows for safe discovery, short-lived
  execution, persistent workspace files, and long-lived reuse.
- Volume-backed checkpoint commands require a workspace volume and fail before
  sandbox creation when no persistent workspace volume is configured.
- CLI `watch` requires a timeout so filesystem events are returned as bounded
  JSON.
- Readiness probe flags apply only at sandbox creation time; `wait-ready`
  attaches to an existing sandbox and waits for its configured Modal readiness
  probe.
- Public source seeding rejects non-HTTP(S) URLs and embedded credentials
  before sandbox creation.
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
with `--workspace-volume`, `snapshot`, `stat`, `sync`, bounded `watch`,
declared-port `domain`, readiness probe waits, and
`start`/`--sandbox-id`/`stop`. Before release, also exercise short-TTL
Modal-native `snapshot-filesystem` and `snapshot-directory` flows manually.
