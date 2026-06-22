# Security

## Resource Safety

- Discovery commands do not create Modal resources.
- Live Modal tests require `MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1`.
- Credentials are inspected only for presence/status in `sandbox doctor`.
- Sandbox network access can be restricted with SDK domain/CIDR allowlists or
  CLI `--allow-domain`, `--allow-cidr`, and `--allow-inbound-cidr`.

## Path Safety

- Relative sandbox paths resolve under the configured workspace.
- Relative paths cannot escape the workspace with `..`.
- Local filesystem transfer is explicit through upload/download helpers.

## Reporting Issues

Do not include Modal tokens or secrets in issues, logs, or docs. Redact `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` before sharing command output.
