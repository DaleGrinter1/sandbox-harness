---
name: modal-sandbox-package-maintenance
description: Package maintenance guidance for modal-sandbox-sdk. Use when changing SDK code, provider behavior, CLI schema, tests, examples, docs, packaging metadata, or release-facing behavior.
---

# Modal Sandbox Package Maintenance

Use this skill when modifying the package. Keep changes small, boring, and
aligned with the existing module boundaries.

## Change Map

- SDK facade: `packages/sandbox/sandbox.py`
- Modal adapter: `packages/sandbox/provider_modal.py`
- CLI contract: `packages/sandbox_cli/cli.py`
- Public data types: `packages/sandbox/commands.py`, `files.py`, `types.py`, `volumes.py`
- Tests: `tests/test_cli.py`, `tests/test_sandbox.py`, `tests/test_provider_modal.py`
- User docs: `README.md`, `docs/references/cli.md`, `docs/references/modal-setup.md`

## Rules

- Keep Modal imported lazily.
- Default tests must not create Modal resources.
- File helpers operate inside the Modal sandbox workspace.
- CLI schema, parser behavior, docs, and tests move together.
- Discovery commands must not instantiate `Sandbox`.
- Nonzero sandbox command exits remain `CommandResult.exit_code`, not exceptions.
- Live Modal validation is opt-in only.

## Validation

Run the narrowest useful checks first:

```bash
uv run pytest tests/test_cli.py
uv run pytest tests/test_sandbox.py tests/test_provider_modal.py
```

Before finishing package changes, run:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv build
uv run sandbox --help
uv run sandbox schema
```

Run live tests only when explicitly requested:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_live.py
```
