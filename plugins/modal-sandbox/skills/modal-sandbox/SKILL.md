---
name: modal-sandbox
description: Run tasks that need isolated, reproducible, or resource-controlled execution in Modal Sandboxes through the modal-sandbox-sdk JSON CLI. Use for untrusted commands, clean runtime experiments, build or test jobs, data workflows, service checks, agent evaluations, controlled workflow benchmarks, persistent remote files, or reusable Modal Sandboxes.
---

# Modal Sandbox

Use the installed `sandbox` command as the execution engine. Do not install the package silently.
Do not invoke it through `uvx`, duplicate its implementation, or use an MCP
server in place of the CLI.

Use this skill when isolation or declared sandbox controls materially improve
the task. Do not use it merely for explanation, planning, an ordinary local
edit, or summarizing results that already exist.

Resolve `<plugin-root>` from this installed `SKILL.md` as two directories up.
Distributed helpers live under `<plugin-root>/scripts/` and must work from any
current working directory.

Treat this plugin as the product surface. The `sandbox` CLI is the JSON engine
that performs checked operations, and the Python SDK is an implementation layer
for the CLI. Do not send users to the SDK first unless they explicitly ask for
Python API usage.

## Preflight

1. Run `sandbox --version`. Require `modal-sandbox-sdk` 0.4.0 or newer. If the
   command is unavailable, stop before any live action and tell the user to run:

   ```bash
   uv tool install modal-sandbox-sdk
   ```

   If an older version is installed, stop and tell the user to run
   `uv tool upgrade modal-sandbox-sdk`. Never change the user's Python
   environment without explicit approval.

2. Run the resource-free discovery sequence:

   ```bash
   sandbox dry
   sandbox doctor
   sandbox schema --agent
   ```

3. Parse each command's JSON output. Require schema version `1`. Use the agent
   schema's `golden_workflows` and run `sandbox schema` only when command-level
   details are needed.
4. Before a live operation, require `doctor.credentials.complete` or
   `doctor.credentials.verified` to be `true`. If both are false, stop and direct interactive users to `modal setup`.
   For non-interactive environments, explain that both `MODAL_TOKEN_ID` and
   `MODAL_TOKEN_SECRET` must be configured; never request that secrets be pasted
   into source files or command history.
5. For a first-time user, run `sandbox quickstart` as a resource-free preview.
   Run `sandbox quickstart --run` only when the user explicitly asks to create
   the first live sandbox.
6. Before a live operation, run `sandbox preview ...` with the intended command
   and summarize the redacted configuration: create versus attach, image,
   workspace, volumes, network policy, resource requests, ports, and env keys.

For one structured resource-free preflight, prefer:

```bash
python <plugin-root>/scripts/preflight.py
```

If Python cannot run the helper, use the direct CLI sequence above.

For a resource-free workflow plan from a user intent, prefer:

```bash
python <plugin-root>/scripts/workflow.py --intent run-tests-safely
```

The distributed workflow examples under `<plugin-root>/examples/` show the
expected plugin plan, safe commands, preview command, live commands, cleanup
commands, and approval boundary for common user prompts.

## Choose a Workflow

- Use `sandbox run` or `sandbox run-command` for one isolated operation.
- Add `--workspace-volume NAME` when files must survive separate CLI calls.
- Use `sandbox.toml` when the same image, volume, env keys, or network flags
  repeat across commands. Explicit CLI flags still win.
- Use `sandbox --name NAME start`, then `--sandbox-name NAME` or
  `--sandbox-id ID`, when multiple operations must share one running sandbox.
- Use `sandbox status` to inspect visible sandbox apps and `sandbox cleanup`
  to preview cleanup. Add `--yes` only after the user authorizes stopping apps.
- Declare ports and readiness probes before starting a service; resolve its URL
  with `domain` only after readiness succeeds.
- For a controlled comparison, create a versioned benchmark manifest and
  validate it without resources:

  ```bash
  python <plugin-root>/scripts/benchmark.py scenario.json --validate-only
  ```

  After explicit authorization for live Modal execution, run:

  ```bash
  python <plugin-root>/scripts/benchmark.py scenario.json --allow-live
  ```

  Compare only equivalent inputs and controls. Report runtime or image,
  resources, region when declared, network policy, warmups, repetitions,
  timeouts, cache state, and the runner's limitations.

Prefer the exact commands returned by `sandbox schema --agent`. Treat relative
paths as relative to the sandbox workspace, not the user's local repository.

## Workflow Examples

- Run tests safely: `<plugin-root>/examples/run-tests-safely.json`
- Debug a failing script: `<plugin-root>/examples/debug-failing-script.json`
- Persist workspace files: `<plugin-root>/examples/persistent-workspace.json`
- Start a reusable coding sandbox: `<plugin-root>/examples/reusable-coding-sandbox.json`
- Benchmark two approaches: `<plugin-root>/examples/benchmark-two-approaches.json`
- Inspect and clean up resources: `<plugin-root>/examples/inspect-and-cleanup.json`

## Live-Action Boundary

- Run live Modal commands only when the user asked for execution or explicitly
  approved the live step. Discovery, explanation, and planning requests do not
  authorize resource creation.
- State when the next command creates or contacts a Modal resource.
- Prefer showing the `sandbox preview ...` result before the live command.
- Use a unique, meaningful name for agent-created volumes and reusable
  sandboxes to reduce collisions.
- Wrap long-lived workflows in cleanup logic. Stop an agent-created reusable
  sandbox when the requested work finishes unless the user explicitly asks to
  keep it running. Report any cleanup failure.
- Never run the live test suite unless the user explicitly requests it.
- Never run `sandbox cleanup --yes` unless the user explicitly authorizes
  stopping Modal apps.
- Designing or validating a benchmark does not authorize running it. The
  benchmark helper must receive `--allow-live`, and preflight must report
  complete credentials, before it contacts Modal.
- Treat user-supplied workflow commands as untrusted. Apply requested network
  and resource controls, never place secrets in manifests, and keep repetitions,
  timeouts, and output bounded.

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
