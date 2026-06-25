# Product Specs Index

Product specs define what users should be able to do with `modal-sandbox-sdk`.

## Current Product Surface

- Python SDK for creating Modal Sandboxes, running commands, moving files, and
  using focused Modal-native helpers.
- JSON-first CLI for discovery, command execution, file workflows, volumes,
  filesystem inspection, source seeding, and long-lived sandbox reuse.
- First-class volume mounts through `SandboxVolume` and CLI `--volume NAME:/mount`.
- Vercel-style conveniences for runtime aliases, argv commands, ports, and volume-backed snapshots.
- Readiness probes for service-style sandboxes and reusable workflows.
- Sandbox network allowlisting through SDK domain/CIDR options and CLI
  `--allow-domain`, `--allow-cidr`, and `--allow-inbound-cidr`.

## Specs

- [CLI Golden Workflows](cli-golden-workflows.md)
- [Modal-Native Filesystem And Source Workflows](modal-native-filesystem-and-source.md)
- [Sandbox Network Allowlists](sandbox-domain-allowlist.md)
- [Vercel-Style Conveniences](vercel-style-conveniences.md)
- [Volume-Backed Snapshots](volume-backed-snapshots.md)

## Spec Maintenance

- Add a product spec before changing user-visible SDK or CLI behavior that spans multiple files.
- Keep examples copy-pasteable.
- Link active execution plans under `docs/exec-plans/active/` when implementation is in progress.
