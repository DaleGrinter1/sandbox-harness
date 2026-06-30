# Collaborator Onboarding

This page is for private-team collaborators who want to understand, review, or
contribute docs and examples without first becoming Modal or Python packaging
experts.

## Project Shape

This repository is a lightweight Python SDK and CLI helper for Modal Sandboxes.
It is intentionally not a generic sandbox package.

Use it to:

- Run commands in Modal Sandboxes.
- Move files in and out of the sandbox workspace.
- Keep files across CLI calls with Modal volumes.
- Inspect CLI behavior before creating Modal resources.

The public Python package is `sandbox`. The command-line entry point is
`sandbox`.

## First 30 Minutes

For agent handoff, start with the
[new agent starter prompt](new-agent-prompt.md). It tells agents to use dry
commands first and to check execution-plan state before broad work.

Install dependencies:

```bash
uv sync
```

Run the dry-command safe discovery path. These commands do not create Modal
resources:

```bash
uv run sandbox dry
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
```

Run a focused local test:

```bash
uv run pytest tests/test_cli.py
```

For a compact no-resource walkthrough, use:

```bash
./scripts/dev/quickstart.sh
```

For the default non-live validation suite, use:

```bash
./scripts/dev/check.sh
```

## Where To Look

- `README.md`: product overview, quickstart, SDK snippets, CLI examples.
- `CONTRIBUTING.md`: private-team contribution flow and validation choices.
- `docs/references/cli.md`: stable CLI workflows and command lifecycle notes.
- `docs/references/development.md`: local validation and release checks.
- `examples/`: small SDK and CLI examples to copy or review.

Useful examples for a frontend collaborator:

- `examples/node_dev_server.py`: expose a Node server through a Modal Sandbox
  port.
- `examples/argv_command.py`: run an argv-style command without shell wrapping.
- `examples/volume_mounts.py`: mount workspace and cache volumes.
- `examples/persistent_volume.sh`: keep files across sandbox lifetimes.

## Dry Versus Live Commands

Dry commands / safe discovery commands:

```bash
uv run sandbox dry
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
```

Live commands create or attach to Modal resources:

```bash
uv run sandbox --image py313 quickstart --run
uv run sandbox --image py313 run "python -c 'print(123)'"
uv run sandbox --image py313 start
```

Live tests are opt-in:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 ./scripts/dev/live-smoke.sh
```

Use your normal local Modal authentication setup when live commands are needed.
Do not copy token values into repo docs, examples, issue text, or commits.

## Review Checklist

When reviewing docs or examples, check that:

- Safe discovery examples do not create Modal resources.
- Live examples are labeled clearly.
- CLI schema, docs, and examples agree on command names and lifecycle behavior.
- Generated contracts such as `docs/generated/cli-schema.json` are current when
  CLI metadata changes.
- No Modal tokens, API keys, or token-looking placeholder values were added.
