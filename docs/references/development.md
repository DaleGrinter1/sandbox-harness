# Development

Default tests do not create real Modal resources.

```bash
uv sync
./scripts/dev/check.sh
```

For a shorter no-resource walkthrough, run:

```bash
./scripts/dev/quickstart.sh
```

## Release Checklist

Before cutting a release, run the full local contract:

```bash
./scripts/dev/check.sh
```

When CLI schema metadata changes, regenerate and review
`docs/generated/cli-schema.json`; the default test suite compares it to the
runtime schema.

```bash
./scripts/dev/schema.sh
```

Then check the built package metadata and install path:

```bash
uv run python -m pip install --force-reinstall dist/*.whl
uv run python -c "from sandbox import Sandbox, SandboxImageSnapshot, SandboxVolume; from sandbox.volumes import SandboxVolume as V; assert SandboxVolume is V; assert SandboxImageSnapshot"
uv run sandbox schema
```

Live Modal tests are opt-in:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 ./scripts/dev/live-smoke.sh
```

The live suite creates real Modal resources and covers the beginner acceptance
path: SDK file helpers, `quickstart --run`, CLI file persistence with a
workspace volume, `snapshot`, `stat`, `sync`, bounded `watch`, port `domain`,
readiness probe waits, and `start`/`--sandbox-id`/`stop`. Before release,
manually include short-TTL Modal-native `snapshot-filesystem` and
`snapshot-directory` flows. The persistent volume test uses a unique volume
name and deletes it in cleanup.
