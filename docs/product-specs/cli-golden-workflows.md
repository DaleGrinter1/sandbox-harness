# CLI Golden Workflows

## Summary

Agents and shell users can discover and run a small set of supported Modal
Sandbox workflows through the JSON-first `sandbox` CLI.

## User Goals

- Users can inspect `sandbox schema`, `sandbox doctor`, and `sandbox quickstart`
  without creating Modal resources.
- Users can run one short-lived command and inspect a JSON `CommandResult`.
- Users can persist files across sandbox lifetimes with `--workspace-volume`.
- Users can start a reusable sandbox, attach with `--sandbox-id`, and stop it.

## Behavior

- CLI output is JSON except for `--help` and `--version`.
- `sandbox schema` exposes command metadata, lifecycle notes, auth guidance,
  and `golden_workflows`.
- `schema`, `doctor`, and `quickstart` without `--run` do not instantiate
  `Sandbox`.
- Operational commands create or attach to one sandbox, perform one operation,
  and close according to ownership semantics.
- Invalid lifecycle combinations are rejected before sandbox creation.
- Nonzero sandbox command exits are returned in JSON unless
  `--use-command-exit-code` is set.

## Non-Goals

- No hidden long-running daemon or implicit workspace persistence.
- No text-oriented output mode beyond standard help/version output.
- No live Modal validation in default tests.

## Examples

```bash
sandbox schema
sandbox doctor
sandbox quickstart
sandbox --image py313 run "python -c 'print(123)'"
sandbox --image py313 --workspace-volume work write app.py --content "print(123)"
sandbox --image py313 --workspace-volume work run "python app.py"
sandbox --image py313 start
sandbox --sandbox-id sb-abc123 run "python --version"
sandbox stop sb-abc123
```
