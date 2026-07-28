#!/usr/bin/env python3
"""Resource-free compatibility preflight for the modal-sandbox plugin."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

REQUIRED_SCHEMA_VERSION = "1"
DEFAULT_MIN_VERSION = "0.4.0"


@dataclass
class CliFailure(Exception):
    code: str
    message: str
    command: list[str]
    returncode: int | None = None


def _version_tuple(value: str) -> tuple[int, ...]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", value)
    if match is None:
        raise ValueError(f"could not parse semantic version from {value!r}")
    return tuple(int(part) for part in match.groups())


def _run(
    executable: str,
    arguments: list[str],
    *,
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    command = [executable, *arguments]
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise CliFailure(
            "cli_not_found",
            f"{executable!r} was not found; install it with `uv tool install modal-sandbox-sdk`.",
            command,
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise CliFailure("cli_timeout", f"{' '.join(command)} exceeded {timeout_seconds} seconds.", command) from exc


def _run_json(executable: str, arguments: list[str], *, timeout_seconds: int) -> dict[str, Any]:
    completed = _run(executable, arguments, timeout_seconds=timeout_seconds)
    command = [executable, *arguments]
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no error output"
        raise CliFailure("cli_command_failed", detail, command, completed.returncode)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CliFailure("invalid_cli_json", f"{' '.join(command)} did not return valid JSON.", command) from exc
    if not isinstance(payload, dict):
        raise CliFailure("invalid_cli_json", f"{' '.join(command)} returned a non-object JSON value.", command)
    return payload


def run_preflight(
    executable: str = "sandbox",
    *,
    min_version: str = DEFAULT_MIN_VERSION,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Run only CLI commands documented as resource-free."""

    started_commands: list[list[str]] = []
    try:
        version_result = _run(executable, ["--version"], timeout_seconds=timeout_seconds)
        started_commands.append([executable, "--version"])
        if version_result.returncode != 0:
            raise CliFailure(
                "cli_command_failed",
                version_result.stderr.strip() or "sandbox --version failed",
                [executable, "--version"],
                version_result.returncode,
            )
        installed_version = ".".join(str(part) for part in _version_tuple(version_result.stdout))
        if _version_tuple(installed_version) < _version_tuple(min_version):
            raise CliFailure(
                "cli_outdated",
                f"modal-sandbox-sdk {min_version} or newer is required; run `uv tool upgrade modal-sandbox-sdk`.",
                [executable, "--version"],
            )

        checks: dict[str, dict[str, Any]] = {}
        for name, arguments in (
            ("dry", ["dry"]),
            ("doctor", ["doctor"]),
            ("schema", ["schema", "--agent"]),
            ("quickstart", ["quickstart"]),
            ("preview", ["--image", "py313", "preview", "run", "python", "-c", "print(123)"]),
        ):
            checks[name] = _run_json(executable, arguments, timeout_seconds=timeout_seconds)
            started_commands.append([executable, *arguments])

        schema_version = str(checks["schema"].get("schema_version"))
        if schema_version != REQUIRED_SCHEMA_VERSION:
            raise CliFailure(
                "incompatible_cli_schema",
                f"CLI schema {schema_version!r} is incompatible; expected {REQUIRED_SCHEMA_VERSION!r}.",
                [executable, "schema", "--agent"],
            )
        credentials = checks["doctor"].get("credentials")
        credential_complete = (
            bool(credentials.get("complete") or credentials.get("verified")) if isinstance(credentials, dict) else False
        )
        problems = []
        if not credential_complete:
            problems.append("modal_credentials_incomplete")
        summary = {
            "ready_for_live": credential_complete,
            "safe_to_continue": True,
            "status": "ready_for_live" if credential_complete else "needs_setup",
            "problems": problems,
            "next_action": "preview_live_command" if credential_complete else "complete_modal_setup",
            "next_command": "sandbox quickstart --run" if credential_complete else "sandbox doctor",
            "requires_user_approval": credential_complete,
            "preview_command": "sandbox --image py313 preview run python -c 'print(123)'",
        }
        return {
            "schema_version": "1",
            "ok": True,
            "resource_free": True,
            "cli": {
                "executable": executable,
                "version": installed_version,
                "minimum_version": min_version,
                "schema_version": schema_version,
            },
            "credential_complete": credential_complete,
            "ready_for_live": credential_complete,
            "summary": summary,
            "checks": checks,
            "commands": started_commands,
        }
    except (CliFailure, ValueError) as exc:
        if isinstance(exc, CliFailure):
            error = {
                "code": exc.code,
                "message": exc.message,
                "command": exc.command,
                "returncode": exc.returncode,
            }
        else:
            error = {"code": "invalid_cli_version", "message": str(exc), "command": [executable, "--version"]}
        return {
            "schema_version": "1",
            "ok": False,
            "resource_free": True,
            "ready_for_live": False,
            "summary": {
                "ready_for_live": False,
                "safe_to_continue": False,
                "status": "preflight_failed",
                "problems": [error["code"]],
                "next_action": "fix_preflight_error",
                "next_command": "sandbox doctor",
                "requires_user_approval": False,
            },
            "error": error,
            "commands": started_commands,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sandbox-executable", default=os.environ.get("MODAL_SANDBOX_CLI", "sandbox"))
    parser.add_argument("--min-version", default=DEFAULT_MIN_VERSION)
    parser.add_argument("--timeout", type=int, default=30, dest="timeout_seconds")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.timeout_seconds <= 0:
        print(json.dumps({"schema_version": "1", "ok": False, "error": {"code": "invalid_timeout"}}))
        return 2
    result = run_preflight(
        args.sandbox_executable,
        min_version=args.min_version,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
