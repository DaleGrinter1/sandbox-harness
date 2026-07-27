# Sandbox Workflow Selection And Benchmarking

## Promise

The `modal-sandbox` plugin is discoverable for tasks that need isolated,
reproducible, or resource-controlled execution—not only source-code changes.
It can run controlled comparisons of equivalent workflow scenarios and return
structured evidence without claiming that a small fixture represents an entire
company or production system.

Examples include build and test jobs, data transformations, browser or service
checks, dependency experiments, agent evaluations, and untrusted-process
execution.

## Selection Contract

The skill should activate when the task materially benefits from one or more of:

- isolation from the host;
- a declared runtime, image, CPU, memory, GPU, region, or network policy;
- repeatable command and file execution;
- bounded remote lifecycle and output;
- persistent files through a named volume;
- comparable runs under an equivalent environment.

It should not activate merely because a user asks for planning, explanation, a
local edit, or a benchmark of data already supplied. Discovery and validation
requests remain resource-free. A request to design a benchmark does not
authorize running it.

## Distributed Helpers

The plugin includes standard-library Python helpers:

```bash
python <plugin-root>/scripts/preflight.py
python <plugin-root>/scripts/benchmark.py scenario.json --validate-only
python <plugin-root>/scripts/benchmark.py scenario.json --allow-live
```

`preflight.py` locates the installed `sandbox` CLI, checks the minimum package
and schema versions, and runs only `dry`, `doctor`, `schema --agent`, and
`quickstart`.

`benchmark.py` validates a versioned manifest without contacting Modal by
default. `--allow-live` is mandatory for measured runs. The helper delegates
all sandbox creation and command behavior to the installed CLI.

## Scenario Manifest

The manifest is JSON:

```json
{
  "schema_version": "1",
  "benchmark_id": "python-json-workflow",
  "description": "Compare equivalent JSON transformation commands.",
  "scenarios": [
    {
      "id": "stdlib",
      "command": "python -c \"import json; print(json.dumps({'ok': True}))\"",
      "runtime": "python3.13",
      "setup_command": null,
      "cleanup_command": null,
      "warmups": 1,
      "repetitions": 3,
      "timeout_seconds": 30,
      "sandbox_timeout_seconds": 300,
      "max_output_bytes": 4096,
      "env": {},
      "network": {
        "block": true,
        "allow_domains": [],
        "allow_cidrs": []
      },
      "redact": []
    }
  ]
}
```

Requirements:

- `schema_version` is `"1"`.
- Benchmark and scenario IDs use lower-case letters, digits, dots, `_`, or `-`.
- Each scenario declares exactly one of `runtime` or `image`.
- `command` is required. Optional setup and cleanup commands execute inside the
  same one-shot sandbox command.
- Warmups are between 0 and 5; measured repetitions are between 1 and 20.
- Command and sandbox timeouts and captured output are bounded.
- Environment values are strings. Secrets belong in Modal secrets or the
  caller's approved environment, not committed manifests.
- Network blocking and allowlists are explicit and mutually compatible.
- Literal strings listed in `redact` are replaced in output previews.

## Result Contract

The runner emits one JSON object:

```json
{
  "schema_version": "1",
  "benchmark_id": "python-json-workflow",
  "status": "completed",
  "started_at": "RFC3339 timestamp",
  "finished_at": "RFC3339 timestamp",
  "environment": {
    "cli_version": "0.4.0",
    "cli_schema_version": "1"
  },
  "scenarios": [
    {
      "id": "stdlib",
      "configuration": {},
      "warmups": [],
      "runs": [
        {
          "iteration": 1,
          "duration_seconds": 1.234,
          "exit_code": 0,
          "timed_out": false,
          "stdout_preview": "...",
          "stderr_preview": "",
          "stdout_sha256": "...",
          "stderr_sha256": "...",
          "stdout_truncated": false,
          "stderr_truncated": false,
          "failure_class": null
        }
      ],
      "summary": {
        "completed_runs": 1,
        "successful_runs": 1,
        "min_seconds": 1.234,
        "median_seconds": 1.234,
        "max_seconds": 1.234
      }
    }
  ],
  "limitations": []
}
```

Transport, authentication, malformed JSON, timeout, remote nonzero exit, and
cleanup failures are classified separately. Partial results are retained.

## Comparability Rules

Benchmark reports must disclose the CLI version, CLI schema, runtime or image,
resource settings, region when declared, network policy, cache/persistence
settings, warmups, repetitions, and timeouts. Comparisons are directional
evidence only unless scenarios use equivalent inputs and controls. Host-observed
duration includes sandbox provisioning and CLI overhead.

## Safety And Non-Goals

- No live action without `--allow-live` and authenticated Modal credentials.
- No package installation or credential mutation by plugin helpers.
- No implicit long-lived sandboxes or volumes.
- No unbounded repetitions, timeouts, or output.
- No default live tests.
- No claim to reproduce a proprietary workflow without the owner-supplied
  manifest, inputs, permissions, secrets, and network policy.
- No second implementation of the SDK or CLI inside the plugin.

## Acceptance Scenarios

- A data-processing or workflow-comparison prompt can discover the skill.
- A planning-only prompt produces a manifest or explanation but no live run.
- Validate-only mode works with no CLI or Modal credentials.
- Missing, outdated, malformed, or schema-incompatible CLIs fail with
  actionable JSON.
- A fake CLI proves success, remote nonzero exit, timeout, malformed output,
  partial results, redaction, and cleanup-failure behavior.
- Helpers run from an unrelated working directory on Linux, macOS, and Windows.
