# Modal-Native Filesystem And Source Workflows

## Summary

Users can inspect sandbox filesystem state, create explicit Modal image
snapshots, sync volume-backed workspaces, and seed public source without
turning `modal-sandbox-sdk` into a full Modal backend replacement.

## User Goals

- Python users can call `stat()`, bounded `watch()`, and `sync_workspace()`.
- Python users can call `snapshot_filesystem()`, `snapshot_directory()`,
  `mount_image()`, and `unmount_image()` when they want Modal-native image
  snapshot behavior.
- CLI users can run `stat`, bounded `watch`, `sync`, `snapshot-filesystem`,
  `snapshot-directory`, `mount-image`, and `unmount-image`.
- Users can seed public git repositories or tarballs after sandbox creation.

## Behavior

- `stat` returns JSON-friendly path metadata: path, kind, size, permissions,
  and modified time.
- CLI `watch` requires `--timeout SECONDS` so output remains finite JSON.
- `sync_workspace()` uses argv-style `sync <workspace>` and requires a named
  workspace volume.
- Modal-native snapshot helpers return `SandboxImageSnapshot` metadata with an
  image ID, kind, optional path, and optional TTL.
- Public source seeding uses argv-style commands only.
- Source URLs must be HTTP(S) and must not include embedded credentials.

## Non-Goals

- No generic replacement for Modal's Python SDK.
- No token-taking CLI flags for private git or tarball sources.
- No secret placeholders in examples.
- No default live Modal validation in CI.

## Examples

```python
from sandbox import Sandbox, SandboxVolume

with Sandbox.create(runtime="python3.13", volumes=[SandboxVolume.workspace("work")]) as sb:
    sb.seed_git("https://github.com/example/project.git", destination="src")
    sb.sync_workspace()
    print(sb.stat("src").to_dict())

with Sandbox.create(runtime="python3.13") as sb:
    snapshot = sb.snapshot_directory(".", ttl=7 * 24 * 3600)
    sb.mount_image("restored", snapshot)
```

```bash
sandbox --workspace-volume work seed-git https://github.com/example/project.git --dest src
sandbox --workspace-volume work stat src
sandbox --workspace-volume work sync
sandbox watch . --timeout 5
sandbox snapshot-directory . --ttl 604800
```
