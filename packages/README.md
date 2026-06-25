# Packages

This repo is organized around two packages:

- `sandbox`: the Python SDK for creating and working with Modal Sandboxes.
  It exposes command execution, file helpers, volume-backed workspace
  checkpoints, Modal-native image snapshot metadata, filesystem stat/watch,
  workspace sync, readiness probe waits, and public source seeding helpers.
- `sandbox_cli`: the JSON-first command-line interface installed as
  `sandbox`. It mirrors the SDK surface with safe discovery commands plus live
  Modal commands such as `run`, `run-command`, `snapshot`, `stat`, `watch`,
  `sync`, `wait-ready`, `seed-git`, and `seed-tarball`.
