---
name: modal-sandbox-cli-workflows
description: CLI workflow guidance for modal-sandbox-sdk. Use when running or explaining sandbox CLI commands, choosing safe discovery versus live Modal commands, persisting files with volumes, reusing sandboxes, or interpreting JSON output.
---

# Modal Sandbox CLI Workflows

The CLI command is `sandbox`. Commands print JSON except `--help` and
`--version`; failures use a JSON error envelope.

## Safe Discovery

These commands do not create Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
```

Use `doctor.ready`, `creates_modal_resources`, and `golden_workflows` before
recommending live commands.

## Live Workflow Choices

Short-lived command:

```bash
uv run sandbox --image py313 run "python -c 'print(123)'"
```

Persistent files across separate sandbox lifetimes:

```bash
uv run sandbox --image py313 --workspace-volume work write app.py --content "print(123)"
uv run sandbox --image py313 --workspace-volume work run "python app.py"
uv run sandbox --image py313 --workspace-volume work read app.py
```

Long-lived reuse:

```bash
uv run sandbox --image py313 start
uv run sandbox --sandbox-id <sandbox_id> run "python --version"
uv run sandbox stop <sandbox_id>
```

## Guardrails

- Do not run live Modal commands unless the user asked for live execution.
- Use `--workspace-volume` when separate one-shot commands need shared files.
- Use `start` plus `--sandbox-id` when operations should share one running sandbox.
- `snapshot` requires `--workspace-volume`; without it, expect a JSON runtime error.
- Run live tests only with `MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1`.
