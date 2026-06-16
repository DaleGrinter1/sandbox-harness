# Contributing

Thanks for helping keep this SDK small and useful.

## Development

Install dependencies:

```bash
uv sync
```

Run the default validation suite:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
./scripts/execplan/check.sh
uv build
uv run sandbox --help
```

Default tests must not create real Modal resources. Live Modal tests are opt-in:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_live.py
```

## Release Checklist

1. Update `CHANGELOG.md`.
2. Confirm `pyproject.toml` has the intended version.
3. Run the default validation suite.
4. Run live Modal tests if the change touches provider behavior.
5. Confirm generated contracts such as `docs/generated/cli-schema.json` are current.
6. Build with `uv build`.
7. Install the wheel in a clean environment and verify `sandbox schema`.
8. Confirm `sandbox/py.typed`, focused modules, and public imports are present.
9. Tag the release after the package artifact has been checked.
