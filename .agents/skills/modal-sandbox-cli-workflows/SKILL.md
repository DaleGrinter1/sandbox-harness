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
uv run sandbox dry
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
uv run sandbox --image py313 preview run "python -c 'print(123)'"
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

Project config for repeated flags:

```toml
image = "py313"
workspace_volume = "work"
allow_domain = ["api.openai.com"]
```

Status and cleanup:

```bash
uv run sandbox status
uv run sandbox cleanup --app modal-sandbox-sdk
uv run sandbox cleanup --app modal-sandbox-sdk --yes
```

## Auth

Run `sandbox doctor` before any live command and check `credentials.complete`
or `credentials.verified`:

| `credentials.status` | Action |
|---|---|
| `complete_from_environment` | Proceed when the user asked for live execution |
| `complete_from_modal_toml` | Proceed when the user asked for live execution |
| `partial_environment` | Stop; both `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` must be set |
| `missing_or_unknown` | Stop; report credential gap to the user |

For interactive environments, `uv run modal setup` handles the full flow. For
local token setup, use Modal's prompted `uv run modal token set`. Do not put
token secrets in command arguments.

## Guardrails

- Do not run live Modal commands unless the user asked for live execution.
- Check `credentials.complete` or `credentials.verified` from `sandbox doctor`
  before any live command.
- Run `sandbox preview ...` before a live command when practical.
- Use `--workspace-volume` when separate one-shot commands need shared files.
- Use `start` plus `--sandbox-id` when operations should share one running sandbox.
- `snapshot` requires `--workspace-volume`; without it, expect a JSON runtime error.
- Never run `sandbox cleanup --yes` unless the user explicitly authorizes
  stopping Modal apps.
- Run live tests only with `MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1`.
