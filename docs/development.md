# Development

Default tests do not create real Modal resources.

```bash
uv sync
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv build
uv run sandbox --help
```

Live Modal tests are opt-in:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_live.py
```

The live suite creates real Modal resources and covers the beginner acceptance
path: SDK file helpers, `quickstart --run`, CLI file persistence with a
workspace volume, and `start`/`--sandbox-id`/`stop`. The persistent volume test
uses a unique volume name and deletes it in cleanup.
