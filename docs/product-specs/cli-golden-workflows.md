# CLI Golden Workflows

## Summary

Agents and shell users can discover and run a small set of supported Modal
Sandbox workflows through the JSON-first `sandbox` CLI.

## User Goals

- Users can inspect `sandbox dry`, `sandbox schema`, `sandbox doctor`, and
  `sandbox quickstart` without creating Modal resources.
- Users can run one short-lived command and inspect a JSON `CommandResult`.
- Users can persist files across sandbox lifetimes with `--workspace-volume`.
- Users can inspect files, explicitly sync workspace volumes, and seed public
  source when a workflow needs those steps.
- Users can start a reusable sandbox, attach with `--sandbox-id`, and stop it.
- Users can define readiness probes for newly created sandboxes and wait for
  existing sandbox readiness before continuing a workflow.

## Behavior

- CLI output is JSON except for `--help` and `--version`.
- `sandbox dry` and `sandbox --dry` expose safe discovery commands without
  creating Modal resources.
- `sandbox schema` exposes command metadata, lifecycle notes, auth guidance,
  and `golden_workflows`.
- `dry`, `schema`, `doctor`, and `quickstart` without `--run` do not
  instantiate `Sandbox`.
- Operational commands create or attach to one sandbox, perform one operation,
  and close according to ownership semantics.
- Invalid lifecycle combinations are rejected before sandbox creation.
- Nonzero sandbox command exits are returned in JSON unless
  `--use-command-exit-code` is set.
- CLI `watch` is bounded by required `--timeout`.
- Readiness probe flags apply to sandbox creation; `wait-ready` attaches to an
  existing sandbox and waits for Modal readiness.
- Source seeding commands accept only public HTTP(S) URLs without embedded
  credentials.

## Non-Goals

- No hidden long-running daemon or implicit workspace persistence.
- No text-oriented output mode beyond standard help/version output.
- No live Modal validation in default tests.

## Examples

```bash
sandbox dry
sandbox schema
sandbox doctor
sandbox quickstart
sandbox --image py313 run "python -c 'print(123)'"
sandbox --image py313 --workspace-volume work write app.py --content "print(123)"
sandbox --image py313 --workspace-volume work run "python app.py"
sandbox --image py313 --workspace-volume work stat app.py
sandbox --image py313 --workspace-volume work sync
sandbox --image py313 --workspace-volume work seed-git https://github.com/example/project.git --dest src
sandbox --runtime node24 --encrypted-port 3000 --readiness-tcp 3000 --wait-ready start
sandbox --sandbox-id sb-abc123 wait-ready --timeout 60
sandbox --image py313 start
sandbox --sandbox-id sb-abc123 run "python --version"
sandbox stop sb-abc123
```
