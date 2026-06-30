# Changelog

All notable changes to this project will be documented in this file.

This project follows a small, human-readable changelog. Keep entries grouped by
version and use short bullets under Added, Changed, Fixed, or Removed.

## Unreleased

- Added `sandbox schema --agent` and generated `docs/generated/agent-manifest.json`
  for low-token agent orientation.

## 0.3.0 - 2026-06-25

- Added Pydantic-backed validation for public SDK value objects while keeping
  their dataclass-style constructors and `to_dict()` helpers.
- Added `Sandbox.workspace_checkpoint()` for volume-backed workspace
  checkpoints while keeping `create_snapshot()` as a compatibility alias.
- Added Modal-native image snapshot helpers:
  `snapshot_filesystem()`, `snapshot_directory()`, `mount_image()`, and
  `unmount_image()`.
- Added JSON-friendly `SandboxImageSnapshot`, `SandboxFileStat`, and
  `SandboxWatchEvent` public metadata types.
- Added `SandboxReadinessProbe`, `Sandbox.wait_until_ready()`, creation-time
  readiness probe support, and CLI `wait-ready`/`--wait-ready` workflows.
- Added SDK and CLI filesystem helpers for `stat`, bounded `watch`, and
  workspace-volume `sync`.
- Added public-source seeding helpers and CLI commands for HTTP(S) git
  repositories and tarballs without token-taking flags.
- Added CLI commands `snapshot-filesystem`, `snapshot-directory`,
  `mount-image`, `unmount-image`, `stat`, `watch`, `sync`, `seed-git`, and
  `seed-tarball`.
- Changed the Modal dependency policy to `modal>=1.5,<2`.
- Added CI coverage for Python 3.11, 3.12, and 3.13 plus installed-wheel smoke
  checks.
- Updated README, CLI reference, product specs, reliability docs, and generated
  CLI schema for the expanded 0.3 surface.

## 0.2.0 - 2026-06-16

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
- Added product specs for CLI golden workflows, volume-backed snapshots, and
  Vercel-style conveniences.
- Added generated CLI schema contract checking.
- Added execution-plan state validation to CI.
- Changed the minimum Modal dependency to 1.5.0 for domain allowlists and
  Modal's agent-skill CLI.
- Changed CLI preflight validation to reject invalid lifecycle and global
  configuration before sandbox creation.
- Fixed volume-backed snapshots to avoid invalid local Modal `Volume.commit()`
  calls.
- Fixed live-test Modal volume cleanup compatibility for Modal SDK 1.5.

## 0.1.0

- Initial SDK and CLI for Modal Sandbox command and file workflows.
- Added JSON-first CLI discovery commands, beginner recipes, and opt-in live
  Modal tests.
