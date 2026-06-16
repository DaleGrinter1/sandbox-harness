# Contributing

Thanks for helping keep this SDK small and useful.

Start with [collaborator onboarding](docs/references/collaborator-onboarding.md)
if you are new to the repo or mainly helping with docs, examples, or review.

## Development

Install dependencies:

```bash
uv sync
```

Run the default non-live validation suite:

```bash
./scripts/dev/check.sh
```

For a shorter no-resource walkthrough, run:

```bash
./scripts/dev/quickstart.sh
```

When CLI metadata changes, regenerate and verify the generated schema:

```bash
./scripts/dev/schema.sh
```

Default tests must not create real Modal resources. Live Modal tests are opt-in:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 ./scripts/dev/live-smoke.sh
```

## Private-Team Workflow

Use a short branch name that describes the change, such as
`docs/onboarding` or `cli/schema-copy`.

Open a small pull request with:

- What changed and why.
- The narrowest useful validation command you ran.
- Any docs, examples, generated schema, or live Modal impact.
- A note that no secrets or token-looking placeholders were added.

Create an exec plan before broad behavior changes, release-facing work, or any
change that spans multiple subsystems. Small docs, examples, and narrow tests
do not need one.

## Validation By Change Type

- Docs/examples only: run `./scripts/dev/quickstart.sh` and check links.
- CLI schema or command metadata: run `./scripts/dev/schema.sh` and
  `uv run pytest tests/test_cli.py`.
- SDK or provider behavior: run the focused tests first, then
  `./scripts/dev/check.sh`.
- Live Modal behavior: run `MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1
  ./scripts/dev/live-smoke.sh` after the default checks.

## Secret Hygiene

Do not commit Modal tokens, API keys, or token-looking placeholder values. This
repo intentionally avoids example Modal token values and token placeholders.
Use your normal local Modal authentication setup for live commands.

## Release Checklist

1. Update `CHANGELOG.md`.
2. Confirm `pyproject.toml` has the intended version.
3. Run `./scripts/dev/check.sh`.
4. Run live Modal tests if the change touches provider behavior.
5. Confirm generated contracts such as `docs/generated/cli-schema.json` are current.
6. Build with `uv build`.
7. Install the wheel in a clean environment and verify `sandbox schema`.
8. Confirm `sandbox/py.typed`, focused modules, and public imports are present.
9. Tag the release after the package artifact has been checked.
