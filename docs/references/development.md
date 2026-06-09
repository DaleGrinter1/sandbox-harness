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

## Release Checklist

Before cutting a release, run the full local contract:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv build
uv run sandbox schema
uv run sandbox --help
```

Then check the built package metadata and install path:

```bash
uv run python -m pip install --force-reinstall dist/*.whl
uv run python -c "from sandbox import Sandbox, SandboxVolume; from sandbox.volumes import SandboxVolume as V; assert SandboxVolume is V"
```

Live Modal tests are opt-in:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_live.py
```

The live suite creates real Modal resources and covers the beginner acceptance
path: SDK file helpers, `quickstart --run`, CLI file persistence with a
workspace volume, `snapshot`, port `domain`, and `start`/`--sandbox-id`/`stop`.
The persistent volume test uses a unique volume name and deletes it in cleanup.
