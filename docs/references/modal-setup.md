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
uv run modal token set --token-id <token id> --token-secret <token secret>
```

You can also set `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` in the process
environment.

When Modal reports missing, invalid, or expired credentials, this SDK raises
`ModalAuthenticationError` with setup commands so CLI users and Python callers
get a next step instead of a raw Modal traceback.

SDK exceptions inherit from `SandboxError`. Unexpected provider failures are
wrapped in `SandboxProviderError`; nonzero command exits remain regular
`CommandResult` values and do not raise.
