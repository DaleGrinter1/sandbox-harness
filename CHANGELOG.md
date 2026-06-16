# Changelog

All notable changes to this project will be documented in this file.

This project follows a small, human-readable changelog. Keep entries grouped by
version and use short bullets under Added, Changed, Fixed, or Removed.

## Unreleased

- Added CLI support for runtime aliases, argv-style `run-command`, declared
  sandbox ports, port domains, and volume-backed snapshots.
- Added `SandboxVolume` as a first-class SDK primitive for mounting Modal
  volumes in `Sandbox.create`.
- Added focused public modules for commands, files, errors, and volumes.
- Added `py.typed` so type checkers can use the package's inline types.
- Added CLI `--volume NAME:/mount` for additional Modal volume mounts.
- Added SDK `outbound_domain_allowlist` and CLI `--allow-domain` for sandbox
  outbound domain allowlisting.
- Added docs for using Modal's upstream `modal skills` CLI alongside this
  repo's local agent skills.
- Added SDK examples for argv commands, volume mounts, reusable sandboxes, and
  Node dev servers.
- Added a concise `summary` section to `sandbox doctor` JSON output.
- Changed the minimum Modal dependency to 1.5.0 for domain allowlists and
  Modal's agent-skill CLI.
- Fixed volume-backed snapshots to avoid invalid local Modal `Volume.commit()`
  calls.
- Fixed live-test Modal volume cleanup compatibility for Modal SDK 1.5.

## 0.1.0

- Initial SDK and CLI for Modal Sandbox command and file workflows.
- Added JSON-first CLI discovery commands, beginner recipes, and opt-in live
  Modal tests.
