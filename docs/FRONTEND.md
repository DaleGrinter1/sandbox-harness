# Frontend

This repository does not contain a frontend application.

Frontend-adjacent workflows currently live in the SDK, CLI, and examples:

- Use `runtime="node24"` or `--runtime node24` for Node-based sandbox work.
- Declare ports with `encrypted_ports` in the SDK when a dev server should be
  reachable.
- Use the CLI `domain` command with a reusable `--sandbox-id` to inspect the
  URL for an exposed port.
- Use `--workspace-volume` or `SandboxVolume.workspace(...)` when files need to
  persist across separate sandbox lifetimes.
- See `examples/node_dev_server.py` for the smallest Node server example.

If a frontend is added later:

- Create a product spec under `docs/product-specs`.
- Add a design doc under `docs/design-docs/`.
- Add an exec plan under `docs/exec-plans/active/`.
- Include screenshot or browser-driven validation in the plan state.
