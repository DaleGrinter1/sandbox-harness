# Sandbox Network Allowlists

## Summary

Users can restrict Modal Sandbox network access with domain and CIDR
allowlists.

## User Goals

- Python users can pass `outbound_domain_allowlist=[...]` to `Sandbox.create`.
- Python users can pass `outbound_cidr_allowlist=[...]` for outbound IP ranges.
- Python users can pass `inbound_cidr_allowlist=[...]` for tunnel and connect
  token access.
- CLI users can repeat `--allow-domain DOMAIN` on live sandbox commands.
- CLI users can repeat `--allow-cidr CIDR` and `--allow-inbound-cidr CIDR`.
- Agents can discover the feature through `sandbox schema`.

## Behavior

- Domain allowlists apply when creating a Modal Sandbox.
- CIDR allowlists apply when creating a Modal Sandbox.
- The SDK stores normalized domain values on `SandboxConfig`.
- The SDK stores normalized CIDR values on `SandboxConfig`.
- The Modal provider forwards values to `modal.Sandbox.create` as
  `outbound_domain_allowlist`.
- The Modal provider forwards CIDR values to `modal.Sandbox.create` as
  `outbound_cidr_allowlist` and `inbound_cidr_allowlist`.
- The CLI flag is repeatable and only passes the setting when at least one
  domain is provided.
- CIDR CLI flags are repeatable and only passed when at least one CIDR is
  provided.
- Domain allowlist entries must be hostnames, not URLs.
- CIDR allowlist entries must be valid CIDR ranges.
- `block_network=True` cannot be combined with domain or CIDR allowlists.
- Default discovery commands remain resource-free.

## Non-Goals

- No private networking abstraction beyond Modal's Sandbox allowlist options.
- No live Modal test defaults; live validation remains opt-in.
