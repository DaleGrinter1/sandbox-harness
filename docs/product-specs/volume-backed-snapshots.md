# Volume-Backed Snapshots

## Summary

Users can preserve sandbox workspace files by mounting a named Modal volume at
the workspace path and treating that volume name as snapshot metadata.

## User Goals

- Python users can mount `SandboxVolume.workspace("name")`, write workspace
  files, and call `create_snapshot()`.
- Python users can call `Sandbox.from_snapshot("name")` to mount the same
  workspace volume in a new sandbox.
- CLI users can pass `--workspace-volume NAME` and run `snapshot` to receive
  JSON metadata for that volume-backed checkpoint.

## Behavior

- Snapshot metadata has `name`, `kind: "modal_volume"`, and `workspace`.
- `snapshot` requires `--workspace-volume` and is rejected before sandbox
  creation when no workspace volume is provided.
- The implementation does not call local Modal `Volume.commit()`.
- Snapshot persistence covers files written to the mounted workspace volume.

## Non-Goals

- No full VM filesystem snapshots.
- No process, package-installation, or system-state capture.
- No automatic deletion of user-provided Modal volumes.

## Examples

```python
from sandbox import Sandbox, SandboxVolume

with Sandbox.create(runtime="python3.13", volumes=[SandboxVolume.workspace("work")]) as sb:
    sb.write_text("app.py", "print(123)\n")
    snapshot = sb.create_snapshot()

with Sandbox.from_snapshot(snapshot.name, runtime="python3.13") as sb:
    print(sb.read_text("app.py"))
```

```bash
sandbox --image py313 --workspace-volume work write app.py --content "print(123)"
sandbox --image py313 --workspace-volume work snapshot
```
