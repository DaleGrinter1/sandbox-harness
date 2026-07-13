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

Install local hooks when working on release-facing changes:

```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

Run the manual release hook directly when checking package artifacts:

```bash
uv run pre-commit run release-check --hook-stage manual
```

When CLI schema metadata changes, regenerate and review
`docs/generated/cli-schema.json`; the default test suite compares it to the
runtime schema.

```bash
./scripts/dev/schema.sh
```

Then check the built package metadata and install path:

```bash
./scripts/dev/release-check.sh
```

PyPI publishing uses GitHub trusted publishing. The `Publish` workflow runs
when a GitHub Release is published and expects a protected `pypi` environment
configured in the repository settings. The manual `TestPyPI` workflow expects a
matching `testpypi` environment.

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
