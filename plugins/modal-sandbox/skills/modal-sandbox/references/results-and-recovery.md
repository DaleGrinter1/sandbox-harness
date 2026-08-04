# Results and Recovery

Use the CLI JSON envelope as the source of truth. Preserve the original error
code, message, command result, and resource identifiers in the report.

## Preflight Failures

- `cli_not_found`: stop before live work and recommend
  `uv tool install modal-sandbox-sdk`; do not install it silently.
- `cli_outdated`: stop and recommend `uv tool upgrade modal-sandbox-sdk`.
- `incompatible_cli_schema` or missing capabilities: stop and report the
  expected schema or commands. Do not guess fallback syntax.
- Incomplete credentials: stop and direct interactive users to `modal setup`.
  Never request secrets in chat, files, or command history.
- Invalid or malformed CLI JSON: stop because the plugin cannot safely infer
  state from prose.

## Command Results

- Invalid arguments: correct the input and preview again. Do not create a
  resource while probing syntax.
- Remote nonzero exit: report `exit_code`, stdout, and stderr as a completed
  command result. Change the command only when debugging was requested.
- Timeout: report which bound expired and whether partial output exists.
  Increase timeouts only when the user accepts the tradeoff.
- Truncated output: report the relevant truncation fields. Prefer reading or
  downloading a known artifact before rerunning with a larger output cap.
- Permission or authentication failure: do not retry unchanged.

## Readiness Failures

Report the probe type, declared port or exec command, timeout, sandbox
identifier, and available output. Inspect the original configuration before
retrying. Do not resolve or present a service domain as healthy before the
readiness result succeeds.

## Cleanup Failures

Always report the remaining sandbox or app identifier and the exact preview or
stop command. A failed cleanup must not erase successful command results.
Retry only after checking current status, and never broaden a specific cleanup
into account-wide deletion without new explicit authorization.

Persistent volumes outlive sandbox cleanup by design. Do not delete or imply
deletion of volume data unless the user separately requests it.
