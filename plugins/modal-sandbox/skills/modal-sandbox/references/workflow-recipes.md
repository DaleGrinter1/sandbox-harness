# Workflow Recipes

Use these recipes after preflight and workflow compatibility succeed. Replace
example names, paths, URLs, commands, controls, and ports with user-approved
values. Run each workflow's preview before its live commands.

## Short-Lived Commands

Use `run` for a shell command and `run-command` for argv-style execution.
Apply finite command timeouts and output bounds when work may be noisy or
untrusted. Interpret a nonzero remote exit from the JSON result.

Examples:

```bash
sandbox preview run python -m pytest
sandbox run python -m pytest
```

## Persistent Workspaces

Add `--workspace-volume NAME` when files must survive separate CLI calls.
Verify intended artifacts with `read` or `stat`, call `sync` before another
consumer needs current volume data, and use `snapshot` to report the named
workspace checkpoint. Stopping a sandbox does not authorize deleting its
volume.

## Reusable Sandboxes

Create with `--name NAME start`, then attach with `--sandbox-name NAME` or a
returned sandbox ID. Verify the sandbox with a bounded command or `status`.
Stop it explicitly when the task finishes unless retention was requested.

## Public Source

Use `seed-git` or `seed-tarball` only for public HTTP(S) sources without
embedded credentials. Pair source seeding with a workspace volume when later
commands need the files. Private source access belongs in Modal secrets or a
custom image, not URL or command arguments.

## Services and Readiness

Declare encrypted or unencrypted ports and a TCP or exec readiness probe before
creation. Add `--wait-ready` to creation when the service must be healthy
before continuing. Resolve `domain PORT` only after readiness succeeds, and
stop the named sandbox during cleanup.

## Resource and Network Controls

Declare CPU, memory, GPU, runtime or image, environment keys, and network
policy before preview. `--block-network` cannot be combined with domain or CIDR
allowlists. Do not print environment values from preview output or silently
relax controls when a command fails.

## Filesystem Inspection and Snapshots

Use `stat` for metadata and `watch --timeout SECONDS` for finite event results.
Use `sync` with a workspace volume. Distinguish the volume-backed `snapshot`
result from Modal-native `snapshot-filesystem` or `snapshot-directory` image
metadata.

## Benchmarks

Validate the versioned manifest before requesting live approval. Compare only
equivalent inputs and controls. Report image or runtime, declared resources and
region, network policy, warmups, repetitions, timeouts, cache state, partial
runs, and runner limitations.

## Inspection and Cleanup

Use `sandbox status` to inspect visible apps. Run `sandbox cleanup --app NAME`
without `--yes` to preview targets. Require separate explicit authorization
before adding `--yes`; report each result and verify with `status`.
