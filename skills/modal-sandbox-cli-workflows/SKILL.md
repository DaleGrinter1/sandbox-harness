---
name: modal-sandbox-cli-workflows
description: JSON-first CLI workflow guidance for modal-sandbox-sdk. Use when Codex needs to run commands, choose between one-shot and long-lived Modal Sandbox workflows, use image aliases, interpret command results, or manage sandbox lifecycle through the sandbox CLI.
---

# Modal Sandbox CLI Workflows

Use the `sandbox` CLI for agent-friendly JSON output. Commands print JSON except `--help` and `--version`.

## Discover Before Acting

Run safe discovery before live work:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox recipes
```

Use `creates_modal_resources` in command or recipe output to decide whether user approval is needed.

## One-Shot Commands

Use one-shot commands for isolated execution:

```bash
uv run sandbox --image py313 run "python -c 'print(123)'"
```

Use `--use-command-exit-code` only when the caller needs the CLI process to mirror the sandbox command exit code.

## Long-Lived Workflows

Use `start` when multiple commands need one running sandbox:

```bash
uv run sandbox --image py313 start
uv run sandbox --sandbox-id <sandbox_id> run "python --version"
uv run sandbox stop <sandbox_id>
```

Always stop long-lived sandboxes when finished.

## Images And Resources

- Prefer `--image py313` for beginner Python workflows.
- Other aliases include `py312`, `py311`, and `ubuntu24`.
- Use raw registry tags when the user asks for a specific image.
- Pass resource flags such as `--cpu`, `--memory`, `--gpu`, `--region`, and `--block-network` only when needed.

## Error Handling

- Nonzero sandbox command exits are returned in JSON as `exit_code`; they are not automatically CLI failures.
- If Modal setup is unclear, run `uv run sandbox doctor`.
- Do not infer local filesystem side effects from CLI file commands; file helpers operate in the Modal sandbox workspace.
