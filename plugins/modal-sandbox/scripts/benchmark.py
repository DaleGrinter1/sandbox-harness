#!/usr/bin/env python3
"""Validate or run bounded workflow benchmarks through the sandbox JSON CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from preflight import run_preflight

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
MAX_SCENARIOS = 20


class ManifestError(ValueError):
    pass


def _expect_int(value: object, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ManifestError(f"{name} must be an integer between {minimum} and {maximum}")
    return value


def _optional_number(value: object, name: str, minimum: float) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < minimum:
        raise ManifestError(f"{name} must be a number greater than or equal to {minimum}")
    return value


def _strings(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ManifestError(f"{name} must be an array of non-empty strings")
    return value


def validate_manifest(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ManifestError("manifest must be a JSON object")
    if str(payload.get("schema_version")) != "1":
        raise ManifestError('schema_version must be "1"')
    benchmark_id = payload.get("benchmark_id")
    if not isinstance(benchmark_id, str) or ID_PATTERN.fullmatch(benchmark_id) is None:
        raise ManifestError("benchmark_id must be a lower-case identifier of at most 64 characters")
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= MAX_SCENARIOS:
        raise ManifestError(f"scenarios must contain between 1 and {MAX_SCENARIOS} entries")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(scenarios):
        prefix = f"scenarios[{index}]"
        if not isinstance(raw, dict):
            raise ManifestError(f"{prefix} must be an object")
        scenario_id = raw.get("id")
        if not isinstance(scenario_id, str) or ID_PATTERN.fullmatch(scenario_id) is None:
            raise ManifestError(f"{prefix}.id must be a lower-case identifier of at most 64 characters")
        if scenario_id in seen:
            raise ManifestError(f"duplicate scenario id: {scenario_id}")
        seen.add(scenario_id)
        command = raw.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ManifestError(f"{prefix}.command must be a non-empty string")
        runtime = raw.get("runtime")
        image = raw.get("image")
        if (isinstance(runtime, str) and runtime) == (isinstance(image, str) and image):
            raise ManifestError(f"{prefix} must declare exactly one of runtime or image")
        setup = raw.get("setup_command")
        cleanup = raw.get("cleanup_command")
        if setup is not None and (not isinstance(setup, str) or not setup.strip()):
            raise ManifestError(f"{prefix}.setup_command must be null or a non-empty string")
        if cleanup is not None and (not isinstance(cleanup, str) or not cleanup.strip()):
            raise ManifestError(f"{prefix}.cleanup_command must be null or a non-empty string")
        env = raw.get("env", {})
        if not isinstance(env, dict) or not all(
            isinstance(key, str) and key and isinstance(value, str) for key, value in env.items()
        ):
            raise ManifestError(f"{prefix}.env must map non-empty strings to strings")
        network = raw.get("network", {})
        if not isinstance(network, dict):
            raise ManifestError(f"{prefix}.network must be an object")
        block_network = network.get("block", False)
        if not isinstance(block_network, bool):
            raise ManifestError(f"{prefix}.network.block must be a boolean")
        allow_domains = _strings(network.get("allow_domains", []), f"{prefix}.network.allow_domains")
        allow_cidrs = _strings(network.get("allow_cidrs", []), f"{prefix}.network.allow_cidrs")
        if block_network and (allow_domains or allow_cidrs):
            raise ManifestError(f"{prefix}.network.block cannot be combined with allowlists")

        normalized.append(
            {
                "id": scenario_id,
                "command": command,
                "runtime": runtime if isinstance(runtime, str) else None,
                "image": image if isinstance(image, str) else None,
                "setup_command": setup,
                "cleanup_command": cleanup,
                "warmups": _expect_int(raw.get("warmups", 0), f"{prefix}.warmups", 0, 5),
                "repetitions": _expect_int(raw.get("repetitions", 1), f"{prefix}.repetitions", 1, 20),
                "timeout_seconds": _expect_int(raw.get("timeout_seconds", 30), f"{prefix}.timeout_seconds", 1, 3600),
                "sandbox_timeout_seconds": _expect_int(
                    raw.get("sandbox_timeout_seconds", 300), f"{prefix}.sandbox_timeout_seconds", 1, 86400
                ),
                "max_output_bytes": _expect_int(
                    raw.get("max_output_bytes", 4096), f"{prefix}.max_output_bytes", 0, 1048576
                ),
                "env": dict(sorted(env.items())),
                "network": {
                    "block": block_network,
                    "allow_domains": allow_domains,
                    "allow_cidrs": allow_cidrs,
                },
                "redact": _strings(raw.get("redact", []), f"{prefix}.redact"),
                "cpu": _optional_number(raw.get("cpu"), f"{prefix}.cpu", 0.01),
                "memory": _optional_number(raw.get("memory"), f"{prefix}.memory", 1),
                "gpu": raw.get("gpu") if isinstance(raw.get("gpu"), str) else None,
                "region": raw.get("region") if isinstance(raw.get("region"), str) else None,
            }
        )
    return {
        "schema_version": "1",
        "benchmark_id": benchmark_id,
        "description": payload.get("description") if isinstance(payload.get("description"), str) else None,
        "scenarios": normalized,
    }


def _remote_command(scenario: dict[str, Any]) -> str:
    command = scenario["command"]
    if scenario["setup_command"]:
        command = f"({scenario['setup_command']}) && ({command})"
    if scenario["cleanup_command"]:
        command = (
            f"({command}); benchmark_status=$?; ({scenario['cleanup_command']}); "
            "benchmark_cleanup_status=$?; "
            "if [ $benchmark_cleanup_status -ne 0 ]; then "
            "echo modal-sandbox-benchmark-cleanup-failed >&2; exit 125; fi; "
            "exit $benchmark_status"
        )
    return command


def _cli_arguments(scenario: dict[str, Any]) -> list[str]:
    arguments: list[str] = []
    if scenario["runtime"]:
        arguments.extend(["--runtime", scenario["runtime"]])
    else:
        arguments.extend(["--image", scenario["image"]])
    arguments.extend(
        [
            "--timeout",
            str(scenario["timeout_seconds"]),
            "--sandbox-timeout",
            str(scenario["sandbox_timeout_seconds"]),
            "--max-output-bytes",
            str(scenario["max_output_bytes"]),
        ]
    )
    for key, value in scenario["env"].items():
        arguments.extend(["--env", f"{key}={value}"])
    if scenario["network"]["block"]:
        arguments.append("--block-network")
    for domain in scenario["network"]["allow_domains"]:
        arguments.extend(["--allow-domain", domain])
    for cidr in scenario["network"]["allow_cidrs"]:
        arguments.extend(["--allow-cidr", cidr])
    for option in ("cpu", "memory", "gpu", "region"):
        if scenario[option] is not None:
            arguments.extend([f"--{option}", str(scenario[option])])
    return [*arguments, "run", _remote_command(scenario)]


def _redact(value: str, literals: list[str], maximum: int) -> str:
    for literal in literals:
        value = value.replace(literal, "[REDACTED]")
    return value[:maximum]


def _failure_class(payload: dict[str, Any], returncode: int) -> str | None:
    if returncode != 0:
        return "cli_transport"
    if payload.get("timed_out") or payload.get("exit_code") == 124:
        return "timeout"
    if payload.get("exit_code") == 125 and "modal-sandbox-benchmark-cleanup-failed" in str(payload.get("stderr", "")):
        return "cleanup"
    if payload.get("exit_code") not in (0, None):
        return "remote_nonzero"
    return None


def _run_once(executable: str, scenario: dict[str, Any], iteration: int) -> dict[str, Any]:
    arguments = _cli_arguments(scenario)
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [executable, *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=scenario["sandbox_timeout_seconds"] + 30,
        )
        duration = time.perf_counter() - started
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {
            "iteration": iteration,
            "duration_seconds": round(time.perf_counter() - started, 6),
            "exit_code": None,
            "timed_out": isinstance(exc, subprocess.TimeoutExpired),
            "failure_class": "cli_transport",
            "error": str(exc),
        }

    raw = completed.stdout if completed.stdout.strip() else completed.stderr
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise json.JSONDecodeError("expected object", raw, 0)
    except json.JSONDecodeError:
        return {
            "iteration": iteration,
            "duration_seconds": round(duration, 6),
            "exit_code": None,
            "timed_out": False,
            "failure_class": "malformed_cli_json",
            "error": _redact(raw, scenario["redact"], scenario["max_output_bytes"]),
        }

    stdout = str(payload.get("stdout", ""))
    stderr = str(payload.get("stderr", ""))
    return {
        "iteration": iteration,
        "duration_seconds": round(duration, 6),
        "exit_code": payload.get("exit_code"),
        "timed_out": bool(payload.get("timed_out", False)),
        "stdout_preview": _redact(stdout, scenario["redact"], scenario["max_output_bytes"]),
        "stderr_preview": _redact(stderr, scenario["redact"], scenario["max_output_bytes"]),
        "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
        "stdout_truncated": bool(payload.get("stdout_truncated", False)),
        "stderr_truncated": bool(payload.get("stderr_truncated", False)),
        "failure_class": _failure_class(payload, completed.returncode),
    }


def _preview_scenario(executable: str, scenario: dict[str, Any]) -> dict[str, Any]:
    arguments = [*(_cli_arguments(scenario)[:-2]), "preview", "run", _remote_command(scenario)]
    try:
        completed = subprocess.run(
            [executable, *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "command": [executable, *arguments]}
    try:
        payload = json.loads(completed.stdout)
        if not isinstance(payload, dict):
            raise json.JSONDecodeError("expected object", completed.stdout, 0)
    except json.JSONDecodeError:
        payload = {"error": completed.stderr.strip() or completed.stdout.strip()}
    return {"ok": completed.returncode == 0, "command": [executable, *arguments], "payload": payload}


def _summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    durations = [float(run["duration_seconds"]) for run in runs]
    successful = [run for run in runs if run.get("failure_class") is None]
    return {
        "completed_runs": len(runs),
        "successful_runs": len(successful),
        "min_seconds": min(durations) if durations else None,
        "median_seconds": statistics.median(durations) if durations else None,
        "max_seconds": max(durations) if durations else None,
    }


def run_benchmark(manifest: dict[str, Any], executable: str) -> dict[str, Any]:
    preflight = run_preflight(executable)
    if not preflight["ok"] or not preflight.get("ready_for_live"):
        return {
            "schema_version": "1",
            "benchmark_id": manifest["benchmark_id"],
            "status": "preflight_failed",
            "preflight": preflight,
            "scenarios": [],
        }

    started_at = datetime.now(UTC)
    results = []
    has_failures = False
    for scenario in manifest["scenarios"]:
        preview = _preview_scenario(executable, scenario)
        warmups = [_run_once(executable, scenario, index + 1) for index in range(scenario["warmups"])]
        runs = [_run_once(executable, scenario, index + 1) for index in range(scenario["repetitions"])]
        has_failures = has_failures or any(run.get("failure_class") is not None for run in [*warmups, *runs])
        configuration = {key: value for key, value in scenario.items() if key not in {"command", "redact"}}
        results.append(
            {
                "id": scenario["id"],
                "configuration": configuration,
                "preview": preview,
                "warmups": warmups,
                "runs": runs,
                "summary": _summary(runs),
            }
        )
    finished_at = datetime.now(UTC)
    return {
        "schema_version": "1",
        "benchmark_id": manifest["benchmark_id"],
        "description": manifest["description"],
        "status": "completed_with_failures" if has_failures else "completed",
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "environment": {
            "cli_version": preflight["cli"]["version"],
            "cli_schema_version": preflight["cli"]["schema_version"],
        },
        "scenarios": results,
        "limitations": [
            "Durations are host-observed and include CLI and sandbox provisioning overhead.",
            "Comparisons are meaningful only for equivalent inputs and declared controls.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--sandbox-executable", default=os.environ.get("MODAL_SANDBOX_CLI", "sandbox"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        manifest = validate_manifest(payload)
    except (OSError, json.JSONDecodeError, ManifestError) as exc:
        print(
            json.dumps(
                {"schema_version": "1", "status": "invalid_manifest", "error": {"message": str(exc)}},
                indent=2,
            )
        )
        return 2
    if args.validate_only:
        print(
            json.dumps(
                {
                    "schema_version": "1",
                    "status": "valid",
                    "resource_free": True,
                    "benchmark_id": manifest["benchmark_id"],
                    "scenario_count": len(manifest["scenarios"]),
                },
                indent=2,
            )
        )
        return 0
    if not args.allow_live:
        print(
            json.dumps(
                {
                    "schema_version": "1",
                    "status": "live_authorization_required",
                    "resource_free": True,
                    "error": {"message": "Pass --allow-live only after the user authorizes live Modal execution."},
                },
                indent=2,
            )
        )
        return 2
    result = run_benchmark(manifest, args.sandbox_executable)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
