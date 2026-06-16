# Sandbox Domain Allowlist

## Summary

Users can restrict outbound network access from Modal Sandboxes to an explicit
list of domains.

## User Goals

- Python users can pass `outbound_domain_allowlist=[...]` to `Sandbox.create`.
- CLI users can repeat `--allow-domain DOMAIN` on live sandbox commands.
- Agents can discover the feature through `sandbox schema`.

## Behavior

- Domain allowlists apply when creating a Modal Sandbox.
- The SDK stores normalized domain values on `SandboxConfig`.
- The Modal provider forwards values to `modal.Sandbox.create` as
  `outbound_domain_allowlist`.
- The CLI flag is repeatable and only passes the setting when at least one
  domain is provided.
- Default discovery commands remain resource-free.

## Non-Goals

- No domain syntax validation beyond rejecting empty SDK values.
- No changes to inbound networking, CIDR allowlists, or live Modal test
  defaults.
