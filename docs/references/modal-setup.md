# Modal Setup

Live runs require Modal credentials. If you are new to Modal, create/sign in to
your Modal account and run:

```bash
uv run modal setup
```

If your shell cannot find the `modal` command, use:

```bash
uv run python -m modal setup
```

For non-interactive environments such as CI, configure a Modal token instead:

```bash
uv run modal token new
```

You can also set `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` in the process
environment using your normal secret manager.

When Modal reports missing, invalid, or expired credentials, this SDK raises
`ModalAuthenticationError` with setup commands so CLI users and Python callers
get a next step instead of a raw Modal traceback.

SDK exceptions inherit from `SandboxError`. Unexpected provider failures are
wrapped in `SandboxProviderError`; nonzero command exits remain regular
`CommandResult` values and do not raise.

## Operational Notes

- `sandbox doctor` and `sandbox quickstart` are safe discovery commands and do
  not create Modal resources.
- `sandbox quickstart --run` creates a short-lived sandbox and should be the
  first live acceptance check after credentials are configured.
- Separate one-shot CLI commands do not share filesystem state unless they use
  the same `--workspace-volume` or attach to the same `--sandbox-id`.
- `--readiness-tcp` and `--readiness-exec` define Modal readiness probes only
  for newly created sandboxes. Use `--wait-ready` to wait immediately, or
  `sandbox --sandbox-id ... wait-ready` to wait after `start`.
- `sandbox snapshot` requires `--workspace-volume`; the snapshot response is
  metadata for the mounted workspace volume, not a full VM image.
- `sandbox snapshot-filesystem` and `sandbox snapshot-directory` create
  Modal-native image snapshots and return image metadata.
- `sandbox seed-git` and `sandbox seed-tarball` accept public HTTP(S) sources
  only. Use Modal secrets, a custom image, or a setup command inside the
  sandbox for private sources.
- Volume names are Modal account resources. Use unique names for tests and
  cleanup throwaway volumes after live validation.
