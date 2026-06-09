# Reliability

## Guarantees

- Default tests do not create real Modal resources.
- Nonzero sandbox command exits are returned as `CommandResult.exit_code`, not raised.
- CLI runtime and argument failures use JSON error envelopes.
- Attached sandboxes detach on close; created sandboxes terminate on close.

## Validation

```bash
uv run pytest
uv run ruff check .
uv run pyright
./scripts/execplan/check.sh
```

Live Modal validation is opt-in:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_live.py
```
