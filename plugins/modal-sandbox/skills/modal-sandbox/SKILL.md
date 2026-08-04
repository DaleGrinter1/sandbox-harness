---
name: modal-sandbox
description: Plan, validate, and run tasks that need isolated, reproducible, or resource-controlled execution in Modal Sandboxes through the modal-sandbox-sdk JSON CLI. Use for untrusted commands, clean runtime experiments, public source seeding, build or test jobs, data workflows, services with readiness checks, filesystem inspection, agent evaluations, controlled benchmarks, persistent remote files, or reusable Modal Sandboxes.
---

# Modal Sandbox

Treat this plugin as the product surface, the installed `sandbox` CLI as its
JSON execution engine, and the Python SDK as the lower-level implementation.
Do not duplicate the CLI, replace it with an MCP server, invoke it through
`uvx`, or install or upgrade packages without explicit approval.

Resolve `<plugin-root>` as two directories above this installed `SKILL.md`.
Resolve every distributed script, example, and reference from that root so the
plugin works from any current directory.

## Safe Workflow

1. Run the distributed resource-free preflight:

   ```bash
   python <plugin-root>/scripts/preflight.py
   ```

   Require `modal-sandbox-sdk` 0.4.1 or newer and CLI schema `1`. If Python
   cannot run the helper, run `sandbox --version`, `sandbox dry`,
   `sandbox doctor`, `sandbox schema --agent`, and `sandbox quickstart`.
   On `cli_not_found`, stop and recommend
   `uv tool install modal-sandbox-sdk`. On `cli_outdated`, stop and recommend
   `uv tool upgrade modal-sandbox-sdk`. Never perform either change silently.

2. Select the closest workflow and generate a version 2 plan:

   ```bash
   python <plugin-root>/scripts/workflow.py --intent run-tests-safely
   ```

3. Check the workflow against the installed CLI without creating resources:

   ```bash
   python <plugin-root>/scripts/workflow.py \
     --intent run-tests-safely \
     --check-compatibility
   ```

   Continue only when the result status is `ready`. Treat `blocked` as a setup
   problem and `incompatible` as a CLI version, schema, or capability problem.

4. Run every `preview_commands` entry and summarize its redacted image,
   workspace, volumes, network policy, resources, ports, readiness probe, and
   environment keys.
5. Ask for explicit approval before `live_commands`. A planning, explanation,
   preview, benchmark-design, or readiness-only request never grants approval.
6. Run approved live commands through `sandbox`, parse their JSON envelopes,
   then run `verification_commands`.
7. Preview cleanup first. Run a cleanup command containing `--yes`, or any
   command that stops a sandbox, only after explicit cleanup authorization.

## Workflow Routing

Activate this skill for Modal-sandbox-specific planning, preflight, preview, and
benchmark design even when live execution is forbidden; keep those requests
resource-free. Select and report exactly one canonical workflow ID below when
the intent matches. Do not invent a new workflow ID.

- `run-tests-safely`: one bounded isolated test run.
- `debug-failing-script`: reproduce and inspect a failure in a clean runtime.
- `persistent-workspace`: preserve and verify files across separate runs.
- `reusable-coding-sandbox`: share one named live sandbox across operations.
- `seed-and-test-project`: seed public Git or tarball source, then test it.
- `service-with-readiness`: declare ports and probes, resolve a domain, stop.
- `resource-controlled-job`: declare compute, environment, and network limits.
- `filesystem-inspection`: stat, watch, sync, and snapshot workspace state.
- `benchmark-two-approaches`: compare equivalent bounded scenarios.
- `inspect-and-cleanup`: inspect apps and perform separately approved cleanup.

Read [workflow-recipes.md](references/workflow-recipes.md) when selecting or
adapting commands for one of these workflows. Prefer exact capabilities from
`sandbox schema --agent`; relative paths resolve inside the sandbox workspace.

## Live-Action Boundary

- Require `doctor.credentials.complete` or `doctor.credentials.verified` before
  live work. Otherwise direct interactive users to `modal setup`; in
  non-interactive environments, name `MODAL_TOKEN_ID` and
  `MODAL_TOKEN_SECRET` without requesting secret values in chat or source.
- State when the next command contacts Modal or creates a resource.
- Use unique meaningful names for agent-created volumes and reusable sandboxes.
- Bound command time, output, filesystem watches, and benchmark repetitions.
- Never silently relax network or resource controls after a failure.
- Stop agent-created reusable sandboxes when work finishes unless the user asks
  to retain them. Preserve persistent volume data unless deletion is separately
  authorized.
- Never run live tests or `sandbox cleanup --yes` without explicit approval.

## Results and Recovery

Report the expected fields declared by the workflow. For command results,
include `exit_code`, `stdout`, `stderr`, `timed_out`, and any truncation fields.
A nonzero remote exit is a completed command result, not automatically a CLI
transport failure.

Read [results-and-recovery.md](references/results-and-recovery.md) when a
preflight, command, readiness probe, result, or cleanup step fails. Do not retry
authentication, permission, invalid-argument, or destructive operations
unchanged.

For benchmarks, validate first and run only after live authorization:

```bash
python <plugin-root>/scripts/benchmark.py scenario.json --validate-only
python <plugin-root>/scripts/benchmark.py scenario.json --allow-live
```
