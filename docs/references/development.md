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
`docs/generated/cli-schema.json` and `docs/generated/agent-manifest.json`;
the default test suite compares them to the runtime schema. Also review the
public skill at `plugins/modal-sandbox/skills/modal-sandbox/SKILL.md` because it
uses schema version 1 as its capability contract.

```bash
./scripts/dev/schema.sh
```

Then check the built package metadata and install path:

```bash
./scripts/dev/release-check.sh
```

The release check also validates the repo-local marketplace, plugin manifest,
and skill contract. Plugin releases are independent from package releases;
plugin `0.1.x` is tested against CLI schema version `1`, not one exact package
version.

## Local Plugin Iteration

The repo-local marketplace lives at `.agents/plugins/marketplace.json`. Add it
once, install the plugin, and start a new Codex thread:

```bash
codex plugin marketplace add .agents/plugins
codex plugin add modal-sandbox@personal
```

After editing an already-installed local plugin, update its Codex cachebuster
without changing its base version, reinstall it, and start another new thread:

```bash
uv run python scripts/dev/update-plugin-cachebuster.py plugins/modal-sandbox
codex plugin add modal-sandbox@personal
```

Do not hand-edit marketplace configuration during this update loop.

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
