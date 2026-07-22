---
name: modal-sandbox
description: Run coding tasks in Modal Sandboxes through the modal-sandbox-sdk JSON CLI. Use when Codex needs to execute code or tests in isolation, manipulate remote sandbox files, persist a workspace with a Modal volume, expose a sandbox service, or create and reuse a long-lived Modal Sandbox.
---

# Modal Sandbox

Use the installed `sandbox` command as the execution engine. Do not install the package silently.
Do not invoke it through `uvx`, duplicate its implementation, or use an MCP
server in place of the CLI.

## Preflight

1. Run `sandbox --version`. If the command is unavailable, stop before any
   live action and tell the user to run:

   ```bash
   pip install modal-sandbox-sdk
   ```

2. Run the resource-free discovery sequence:

   ```bash
   sandbox dry
   sandbox doctor
   sandbox schema --agent
   ```

3. Parse each command's JSON output. Require schema version `1`. Use the agent
   schema's `golden_workflows` and run `sandbox schema` only when command-level
   details are needed.
4. Before a live operation, require `doctor.credentials.authenticated` to be
   `true`. If it is false, stop and direct interactive users to `modal setup`.
   For non-interactive environments, explain that both `MODAL_TOKEN_ID` and
   `MODAL_TOKEN_SECRET` must be configured; never request that secrets be pasted
   into source files or command history.

## Choose a Workflow

- Use `sandbox run` or `sandbox run-command` for one isolated operation.
- Add `--workspace-volume NAME` when files must survive separate CLI calls.
- Use `sandbox --name NAME start`, then `--sandbox-name NAME` or
  `--sandbox-id ID`, when multiple operations must share one running sandbox.
- Declare ports and readiness probes before starting a service; resolve its URL
  with `domain` only after readiness succeeds.

Prefer the exact commands returned by `sandbox schema --agent`. Treat relative
paths as relative to the sandbox workspace, not the user's local repository.

## Live-Action Boundary

- Run live Modal commands only when the user asked for execution or explicitly
  approved the live step. Discovery, explanation, and planning requests do not
  authorize resource creation.
- State when the next command creates or contacts a Modal resource.
- Use a unique, meaningful name for agent-created volumes and reusable
  sandboxes to reduce collisions.
- Wrap long-lived workflows in cleanup logic. Stop an agent-created reusable
  sandbox when the requested work finishes unless the user explicitly asks to
  keep it running. Report any cleanup failure.
- Never run the live test suite unless the user explicitly requests it.

## Results and Errors

- Read the CLI JSON envelope instead of inferring success from prose.
- For command results, report `exit_code`, `stdout`, `stderr`, `timed_out`, and
  truncation fields that affect the result. A nonzero sandbox command exit is a
  completed command result, not automatically a CLI transport failure.
- Add `--use-command-exit-code` only when the surrounding shell must receive the
  remote command's exit status.
- Surface CLI error codes and suggested fixes without inventing fallback
  behavior. Do not retry authentication, permission, or invalid-argument errors
  unchanged.
