"""Command-line interface for Modal Sandbox workflows."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import tomllib
from importlib import metadata
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any, NoReturn, cast

from sandbox import Images, ModalAuthenticationError, Sandbox, SandboxReadinessProbe, SandboxVolume

SETUP_COMMANDS = [
    "modal setup",
    "python -m modal setup",
    "modal token new",
    "Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in the environment for non-interactive use.",
]

CLI_SCHEMA_VERSION = "1"
QUICKSTART_COMMAND = "python -c 'print(123)'"
DEFAULT_ERROR_NEXT_STEPS = ["Run `sandbox doctor` to inspect local setup without creating Modal resources."]
_USE_ARG_SANDBOX_ID = object()

IMAGE_ALIASES = {
    "py313": Images.PY313,
    "python313": Images.PY313,
    "python-313": Images.PY313,
    "py312": Images.PY312,
    "python312": Images.PY312,
    "python-312": Images.PY312,
    "py311": Images.PY311,
    "python311": Images.PY311,
    "python-311": Images.PY311,
    "ubuntu24": Images.UBUNTU24,
    "ubuntu-24": Images.UBUNTU24,
}

RECOMMENDED_FIRST_COMMANDS = [
    {
        "command": "sandbox dry",
        "creates_modal_resources": False,
        "purpose": "List safe discovery commands before taking action.",
    },
    {
        "command": "sandbox schema",
        "creates_modal_resources": False,
        "purpose": "Inspect the CLI contract before taking action.",
    },
    {
        "command": "sandbox doctor",
        "creates_modal_resources": False,
        "purpose": "Check local Modal package and credential readiness.",
    },
    {
        "command": "sandbox quickstart",
        "creates_modal_resources": False,
        "purpose": "Preview the first live sandbox command.",
    },
    {
        "command": "sandbox quickstart --run",
        "creates_modal_resources": True,
        "purpose": "Create a short-lived Modal Sandbox and run a tiny Python command.",
    },
]

GOLDEN_WORKFLOWS = [
    {
        "id": "safe_first_run",
        "purpose": "Inspect local readiness before creating Modal resources.",
        "creates_modal_resources": False,
        "commands": [
            "sandbox dry",
            "sandbox schema",
            "sandbox doctor",
            "sandbox quickstart",
        ],
        "success_signal": "quickstart reports ready_to_run or gives setup next steps.",
    },
    {
        "id": "short_lived_command",
        "purpose": "Create one short-lived sandbox and verify command execution.",
        "creates_modal_resources": True,
        "commands": [
            "sandbox --image py313 quickstart --run",
            "sandbox --image py313 run \"python -c 'print(123)'\"",
        ],
        "success_signal": "command JSON has exit_code 0 and expected stdout.",
    },
    {
        "id": "persistent_workspace_files",
        "purpose": "Preserve files across separate CLI calls using a Modal workspace volume.",
        "creates_modal_resources": True,
        "commands": [
            'sandbox --image py313 --workspace-volume work write app.py --content "print(123)"',
            'sandbox --image py313 --workspace-volume work run "python app.py"',
            "sandbox --image py313 --workspace-volume work read app.py",
            "sandbox --image py313 --workspace-volume work snapshot",
            "sandbox --image py313 --workspace-volume work sync",
        ],
        "success_signal": "read returns the file content, snapshot names the workspace volume, and sync exits 0.",
    },
    {
        "id": "long_lived_reuse",
        "purpose": "Reuse one live sandbox for iterative work, then terminate it.",
        "creates_modal_resources": True,
        "commands": [
            "sandbox --image py313 --name agent-workspace start",
            'sandbox --sandbox-name agent-workspace write app.py --content "print(123)"',
            'sandbox --sandbox-name agent-workspace run "python app.py"',
            "sandbox --sandbox-name agent-workspace stop",
        ],
        "success_signal": "start returns sandbox_id and sandbox_name; stop returns status terminated.",
    },
]

PATH_RULES = {
    "relative_paths": "Resolved inside the sandbox workspace.",
    "absolute_paths": "Used as absolute paths inside the sandbox.",
    "workspace_escape": "Relative paths using '..' cannot escape the workspace.",
}

LIVE_MODAL_COMMANDS = [
    "quickstart --run",
    "start",
    "stop",
    "run",
    "run-command",
    "write",
    "read",
    "ls",
    "mkdir",
    "rm",
    "upload",
    "download",
    "domain",
    "wait-ready",
    "snapshot",
    "snapshot-filesystem",
    "snapshot-directory",
    "mount-image",
    "unmount-image",
    "stat",
    "watch",
    "sync",
    "seed-git",
    "seed-tarball",
]

COMMAND_RESULT_SCHEMA = {
    "command": "string",
    "stdout": "string",
    "stderr": "string",
    "exit_code": "integer|null",
    "duration_ms": "integer",
    "timed_out": "boolean",
    "stdout_truncated": "boolean",
    "stderr_truncated": "boolean",
    "max_output_bytes": "integer|null",
}

AGENT_SKILLS = {
    "public_plugin": {
        "path": "plugins/modal-sandbox/skills/modal-sandbox/SKILL.md",
        "purpose": "End-user Codex workflow for safe discovery and authorized Modal Sandbox execution.",
    },
    "repo_understanding": {
        "path": ".agents/skills/modal-sandbox-repo-understanding/SKILL.md",
        "purpose": "Repo orientation, product boundaries, golden workflows, and planning state.",
    },
    "cli_workflows": {
        "path": ".agents/skills/modal-sandbox-cli-workflows/SKILL.md",
        "purpose": "Safe discovery, live Modal command choices, volume workflows, and JSON output interpretation.",
    },
    "package_maintenance": {
        "path": ".agents/skills/modal-sandbox-package-maintenance/SKILL.md",
        "purpose": "SDK, CLI, provider, docs, tests, packaging, and release-facing changes.",
    },
    "understanding_check": {
        "path": ".agents/skills/modal-sandbox-understanding-check/SKILL.md",
        "purpose": "Quiz or coach users on repo architecture, workflows, docs, and validation rules.",
    },
    "modal_upstream": {
        "path": ".agents/skills/modal/SKILL.md",
        "purpose": "Modal-owned SDK guidance when installed; repo-local skills remain source of truth for this package.",
    },
}

COMMANDS_SCHEMA: dict[str, dict[str, Any]] = {
    "start": {
        "summary": "Create a Modal sandbox, print its ID, and leave it running.",
        "creates_sandbox": True,
        "arguments": {},
        "options": {
            "global creation options": "Supports --name, --tag, --image, --runtime, --workspace, --workspace-volume, --volume, --env, network policy, resources, ports, readiness probes, and timeout flags."
        },
        "output": {
            "sandbox_id": "string",
            "status": "started",
            "ready": "boolean when --wait-ready is used",
            "workspace": "string",
            "sandbox_timeout": "integer",
            "use_command": "string",
            "stop_command": "string",
        },
        "example": "sandbox --image python:3.13-slim --name agent-workspace start",
    },
    "stop": {
        "summary": "Terminate a running Modal sandbox by ID or name.",
        "creates_sandbox": False,
        "arguments": {"sandbox_id": "Modal sandbox object ID. Can also be passed with --sandbox-id."},
        "options": {"global --sandbox-name": "Terminate a running named sandbox."},
        "output": {"sandbox_id": "string|null", "sandbox_name": "string|null", "status": "terminated"},
        "example": "sandbox stop sb-abc123",
    },
    "run": {
        "summary": "Run a shell command inside a Modal sandbox.",
        "creates_sandbox": True,
        "arguments": {"command": "Shell command string to run."},
        "options": {
            "--cwd": "Working directory inside the sandbox. Relative paths resolve inside the workspace.",
            "--use-command-exit-code": "Return the sandbox command exit code as the CLI exit code.",
            "global --max-output-bytes": "Maximum captured bytes for stdout and stderr separately. Use 0 to capture no bytes.",
        },
        "output": COMMAND_RESULT_SCHEMA,
        "example": "sandbox --image python:3.13-slim run \"python -c 'print(123)'\"",
    },
    "run-command": {
        "summary": "Run an argv-style command without shell wrapping.",
        "creates_sandbox": True,
        "arguments": {
            "cmd": "Executable to run.",
            "args": "Arguments passed to the executable without shell parsing.",
        },
        "options": {
            "--cwd": "Working directory inside the sandbox. Relative paths resolve inside the workspace.",
            "--env KEY=VALUE": "Per-command environment variable. Repeatable.",
            "--use-command-exit-code": "Return the sandbox command exit code as the CLI exit code.",
            "global --max-output-bytes": "Maximum captured bytes for stdout and stderr separately. Use 0 to capture no bytes.",
        },
        "output": COMMAND_RESULT_SCHEMA,
        "example": "sandbox --runtime python3.13 run-command python -c 'print(123)'",
    },
    "write": {
        "summary": "Write a file inside the sandbox workspace.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {
            "--content": "Inline UTF-8 text content to write.",
            "--content-file": "Local UTF-8 text file to read and write.",
            "--stdin": "Read UTF-8 text from standard input.",
            "--binary-file": "Local binary file to read and write as bytes.",
            "--binary-stdin": "Read raw bytes from standard input and write as binary.",
        },
        "output": {"path": "string", "status": "wrote"},
        "example": 'sandbox --workspace-volume work write hello.py --content "print(123)"',
    },
    "read": {
        "summary": "Read UTF-8 text from a file inside the sandbox workspace.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {},
        "output": {"path": "string", "content": "string"},
        "example": "sandbox --workspace-volume work read hello.py",
    },
    "ls": {
        "summary": "List direct children of a sandbox directory.",
        "creates_sandbox": True,
        "arguments": {"path": "Directory path. Defaults to '.'."},
        "options": {},
        "output": {"path": "string", "files": "string[]"},
        "example": "sandbox --workspace-volume work ls .",
    },
    "mkdir": {
        "summary": "Create a directory inside the sandbox workspace.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {"--no-parents": "Do not create missing parent directories."},
        "output": {"path": "string", "parents": "boolean", "status": "created"},
        "example": "sandbox --workspace-volume work mkdir notes",
    },
    "rm": {
        "summary": "Remove a file or directory inside the sandbox workspace.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {"--recursive": "Remove directories recursively."},
        "output": {"path": "string", "recursive": "boolean", "status": "removed"},
        "example": "sandbox --workspace-volume work rm notes --recursive",
    },
    "upload": {
        "summary": "Copy a local file or directory into the sandbox.",
        "creates_sandbox": True,
        "arguments": {
            "local_path": "Path on the local machine.",
            "remote_path": "Relative workspace path or absolute sandbox path.",
        },
        "options": {},
        "output": {"local_path": "string", "remote_path": "string", "status": "uploaded"},
        "example": "sandbox --workspace-volume work upload input.txt input.txt",
    },
    "download": {
        "summary": "Copy a sandbox file or directory to the local machine.",
        "creates_sandbox": True,
        "arguments": {
            "remote_path": "Relative workspace path or absolute sandbox path.",
            "local_path": "Destination path on the local machine.",
        },
        "options": {},
        "output": {"local_path": "string", "remote_path": "string", "status": "downloaded"},
        "example": "sandbox --workspace-volume work download output.txt output.txt",
    },
    "domain": {
        "summary": "Print the public URL for a declared sandbox port.",
        "creates_sandbox": True,
        "arguments": {"port": "Port declared with --encrypted-port or --unencrypted-port at sandbox creation."},
        "options": {"requires --sandbox-id or --sandbox-name": "Attach to a sandbox created with a declared port."},
        "output": {"port": "integer", "url": "string"},
        "example": "sandbox --sandbox-id sb-abc123 domain 3000",
    },
    "wait-ready": {
        "summary": "Wait for an existing sandbox readiness probe to report ready.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {
            "requires --sandbox-id or --sandbox-name": "Attach to a sandbox that was created with a readiness probe.",
            "--timeout": "Maximum seconds to wait for readiness.",
        },
        "output": {"sandbox_id": "string|null", "sandbox_name": "string|null", "status": "ready", "timeout": "integer"},
        "example": "sandbox --sandbox-id sb-abc123 wait-ready --timeout 60",
    },
    "snapshot": {
        "summary": "Create a volume-backed workspace snapshot checkpoint.",
        "creates_sandbox": True,
        "arguments": {},
        "options": {"requires --workspace-volume": "Snapshot checkpoints are backed by the workspace Modal volume."},
        "output": {"name": "string", "kind": "modal_volume", "workspace": "string", "status": "created"},
        "example": "sandbox --workspace-volume work snapshot",
    },
    "snapshot-filesystem": {
        "summary": "Create a Modal-native filesystem image snapshot.",
        "creates_sandbox": True,
        "arguments": {},
        "options": {
            "--timeout": "Maximum seconds to wait for Modal snapshot creation.",
            "--ttl": "Snapshot TTL in seconds. Use --no-ttl for no expiry.",
            "--no-ttl": "Keep the snapshot indefinitely.",
        },
        "output": {"image_id": "string", "kind": "modal_filesystem", "path": "null", "ttl_seconds": "integer|null"},
        "example": "sandbox snapshot-filesystem --ttl 604800",
    },
    "snapshot-directory": {
        "summary": "Create a Modal-native directory image snapshot.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {
            "--timeout": "Maximum seconds to wait for Modal snapshot creation.",
            "--ttl": "Snapshot TTL in seconds. Use --no-ttl for no expiry.",
            "--no-ttl": "Keep the snapshot indefinitely.",
        },
        "output": {"image_id": "string", "kind": "modal_directory", "path": "string", "ttl_seconds": "integer|null"},
        "example": "sandbox snapshot-directory . --ttl 604800",
    },
    "mount-image": {
        "summary": "Mount a Modal image snapshot inside the sandbox.",
        "creates_sandbox": True,
        "arguments": {"path": "Mount path inside the sandbox.", "image_id": "Modal image object ID."},
        "options": {},
        "output": {"path": "string", "image_id": "string", "status": "mounted"},
        "example": "sandbox --sandbox-id sb-abc123 mount-image project im-abc123",
    },
    "unmount-image": {
        "summary": "Unmount a Modal image snapshot from the sandbox.",
        "creates_sandbox": True,
        "arguments": {"path": "Mount path inside the sandbox."},
        "options": {},
        "output": {"path": "string", "status": "unmounted"},
        "example": "sandbox --sandbox-id sb-abc123 unmount-image project",
    },
    "stat": {
        "summary": "Return metadata for a sandbox filesystem path.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {},
        "output": {
            "path": "string",
            "kind": "string",
            "size": "integer|null",
            "permissions": "string|null",
            "modified_time": "string|null",
        },
        "example": "sandbox --workspace-volume work stat app.py",
    },
    "watch": {
        "summary": "Watch a sandbox path for filesystem changes and return bounded JSON events.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {
            "--timeout": "Required timeout in seconds. The CLI consumes events until the timeout elapses.",
            "--recursive": "Watch nested subdirectories.",
            "--event TYPE": "Event type filter. Repeatable.",
        },
        "output": {"path": "string", "events": "object[]", "recursive": "boolean", "timeout": "integer"},
        "example": "sandbox --sandbox-id sb-abc123 watch . --timeout 5",
    },
    "sync": {
        "summary": "Persist workspace-volume changes without waiting for sandbox termination.",
        "creates_sandbox": True,
        "arguments": {},
        "options": {"requires --workspace-volume": "Workspace sync requires a named workspace Modal volume."},
        "output": COMMAND_RESULT_SCHEMA,
        "example": "sandbox --workspace-volume work sync",
    },
    "seed-git": {
        "summary": "Clone a public Git repository into the sandbox.",
        "creates_sandbox": True,
        "arguments": {"url": "Public HTTP(S) Git repository URL."},
        "options": {
            "--dest PATH": "Destination path inside the sandbox. Defaults to the workspace.",
            "--ref REF": "Optional branch or tag.",
            "--depth N": "Clone depth. Use 0 for a full clone.",
        },
        "output": COMMAND_RESULT_SCHEMA,
        "example": "sandbox --workspace-volume work seed-git https://github.com/org/repo.git --dest .",
    },
    "seed-tarball": {
        "summary": "Download and extract a public tarball into the sandbox.",
        "creates_sandbox": True,
        "arguments": {"url": "Public HTTP(S) tarball URL."},
        "options": {
            "--dest PATH": "Destination path inside the sandbox. Defaults to the workspace.",
            "--strip-components N": "Leading archive path components to remove.",
        },
        "output": COMMAND_RESULT_SCHEMA,
        "example": "sandbox --workspace-volume work seed-tarball https://example.com/source.tar.gz",
    },
    "dry": {
        "summary": "List safe discovery commands that do not create Modal resources.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {"global --dry": "Alias for this command when no subcommand is provided."},
        "output": {
            "status": "string",
            "creates_modal_resources": "false",
            "dry_commands": "string[]",
            "safe_commands": "string[]",
            "recommended_next_command": "string",
            "live_command": "string",
            "checks": "object",
            "next_steps": "string[]",
        },
        "example": "sandbox dry",
    },
    "schema": {
        "summary": "Print this machine-readable CLI schema.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {"--agent": "Print a compact agent manifest instead of the full CLI schema."},
        "output": {"schema_version": "string", "commands": "object"},
        "example": "sandbox schema",
    },
    "auth": {
        "summary": "Write Modal credentials to ~/.modal.toml for non-interactive use.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {
            "--token-id": "Modal token ID (required). Obtain from https://modal.com/settings/tokens.",
            "--token-secret": "Modal token secret (required).",
            "--profile": "Modal config profile to write (default: 'default').",
            "--force": "Overwrite an existing profile entry.",
        },
        "output": {
            "status": "configured",
            "profile": "string",
            "config_path": "string",
            "creates_modal_resources": "false",
        },
        "example": "sandbox auth --token-id ak-... --token-secret as-...",
    },
    "doctor": {
        "summary": "Inspect local Modal package and credential setup, with beginner next steps.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {},
        "output": {
            "ready": "boolean",
            "status": "string",
            "problems": "string[]",
            "next_steps": "string[]",
            "recommended_commands": "object[]",
            "modal_package": "object",
            "credentials": "object",
            "setup_commands": "string[]",
            "creates_modal_resources": "false",
            "summary": "object",
        },
        "example": "sandbox doctor",
    },
    "quickstart": {
        "summary": "Preview or run the first beginner sandbox command.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {
            "--run": "Create a short-lived Modal Sandbox and run the quickstart Python command.",
            "global creation options": "With --run, supports --name, --tag, --image, --runtime, --workspace, --workspace-volume, --volume, --env, network policy, resources, ports, and timeout flags.",
        },
        "output": {
            "creates_modal_resources": "boolean",
            "status": "string",
            "checks": "object",
            "safe_commands": "string[]",
            "live_command": "string",
            "quickstart_command": "string",
            "command": "string when --run is used",
            "stdout": "string when --run is used",
            "stderr": "string when --run is used",
            "exit_code": "integer|null when --run is used",
            "duration_ms": "integer when --run is used",
            "timed_out": "boolean when --run is used",
            "stdout_truncated": "boolean when --run is used",
            "stderr_truncated": "boolean when --run is used",
            "max_output_bytes": "integer|null when --run is used",
            "quickstart": "object when --run is used",
        },
        "example": "sandbox quickstart --run",
    },
}


def _parse_env(values: list[str]) -> dict[str, str]:
    """Parse repeated `--env KEY=VALUE` flags into a dictionary."""
    env: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise argparse.ArgumentTypeError("--env values must use KEY=VALUE")
        key, env_value = value.split("=", 1)
        if not key:
            raise argparse.ArgumentTypeError("--env keys must not be empty")
        env[key] = env_value
    return env


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a non-negative integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be a non-negative integer")
    return parsed


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a positive number") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive number")
    return parsed


def _port(value: str) -> int:
    parsed = _positive_int(value)
    if parsed > 65535:
        raise argparse.ArgumentTypeError("port must be an integer between 1 and 65535")
    return parsed


def _absolute_sandbox_path(value: str) -> str:
    if not value or not value.startswith("/"):
        raise argparse.ArgumentTypeError("value must be an absolute sandbox path")
    return value


def _non_empty_value(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise argparse.ArgumentTypeError("value must not be empty")
    return normalized


def _public_http_url(value: str) -> str:
    normalized = _non_empty_value(value)
    from urllib.parse import urlparse

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("URL must be HTTP(S)")
    if parsed.username or parsed.password:
        raise argparse.ArgumentTypeError("URL must not include embedded credentials")
    return normalized


def _watch_event(value: str) -> str:
    normalized = _non_empty_value(value)
    if not all(character.isalnum() or character in "_-" for character in normalized):
        raise argparse.ArgumentTypeError("watch event names may only contain letters, numbers, dashes, and underscores")
    return normalized


def _readiness_exec(value: str) -> tuple[str, ...]:
    normalized = _non_empty_value(value)
    try:
        parts = tuple(shlex.split(normalized))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"readiness exec command could not be parsed: {exc}") from exc
    if not parts:
        raise argparse.ArgumentTypeError("readiness exec command must not be empty")
    return parts


def _sandbox_name(value: str) -> str:
    normalized = _non_empty_value(value)
    if len(normalized) > 63:
        raise argparse.ArgumentTypeError("sandbox name must be shorter than 64 characters")
    if not all(character.isalnum() or character in ".-_" for character in normalized):
        raise argparse.ArgumentTypeError(
            "sandbox name may only contain letters, numbers, dashes, periods, and underscores"
        )
    return normalized


def _parse_tag(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--tag values must use KEY=VALUE")
    key, tag_value = value.split("=", 1)
    normalized_key = key.strip()
    if not normalized_key:
        raise argparse.ArgumentTypeError("--tag keys must not be empty")
    return normalized_key, tag_value


def _domain_allowlist_value(value: str) -> str:
    normalized = _non_empty_value(value)
    if any(character.isspace() for character in normalized):
        raise argparse.ArgumentTypeError("value must not contain whitespace")
    if any(fragment in normalized for fragment in ("://", "/", "\\", ":", "@")):
        raise argparse.ArgumentTypeError("value must be a hostname, not a URL")

    wildcard = normalized.startswith("*.")
    hostname = normalized[2:] if wildcard else normalized
    if not hostname or len(hostname) > 253 or hostname.startswith(".") or hostname.endswith(".") or ".." in hostname:
        raise argparse.ArgumentTypeError("value must be a valid hostname")
    try:
        ip_address(hostname)
    except ValueError:
        pass
    else:
        raise argparse.ArgumentTypeError("value must be a domain name; use --allow-cidr for IP ranges")

    for label in hostname.split("."):
        if not label or len(label) > 63:
            raise argparse.ArgumentTypeError("value must be a valid hostname")
        if label.startswith("-") or label.endswith("-"):
            raise argparse.ArgumentTypeError("value must be a valid hostname")
        if not all(character.isalnum() or character == "-" for character in label):
            raise argparse.ArgumentTypeError("value must be a valid hostname")
    return normalized


def _cidr_allowlist_value(value: str) -> str:
    normalized = _non_empty_value(value)
    if "/" not in normalized:
        raise argparse.ArgumentTypeError("value must be a CIDR range")
    try:
        ip_network(normalized, strict=False)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a valid CIDR range") from exc
    return normalized


def _parse_volume(value: str) -> SandboxVolume:
    if ":" not in value:
        raise argparse.ArgumentTypeError("--volume values must use NAME:/absolute/path")
    name, mount_path = value.split(":", 1)
    if not name:
        raise argparse.ArgumentTypeError("--volume name must not be empty")
    if not mount_path.startswith("/"):
        raise argparse.ArgumentTypeError("--volume mount path must be absolute")
    return SandboxVolume(volume=name, mount_path=mount_path)


def _resolve_cli_image(image: str | None) -> str | None:
    if image is None:
        return None
    return IMAGE_ALIASES.get(image.lower(), image)


def _volumes_from_args(args: argparse.Namespace) -> tuple[SandboxVolume, ...]:
    volumes = list(args.volume)
    if args.workspace_volume:
        volumes.insert(0, SandboxVolume.workspace(args.workspace_volume, workspace=args.workspace))
    return tuple(volumes)


def _readiness_probe_from_args(args: argparse.Namespace) -> SandboxReadinessProbe | None:
    if args.readiness_tcp is not None:
        return SandboxReadinessProbe.tcp(args.readiness_tcp, interval_ms=args.readiness_interval_ms)
    if args.readiness_exec is not None:
        return SandboxReadinessProbe.exec(args.readiness_exec, interval_ms=args.readiness_interval_ms)
    return None


def _sandbox_from_args(args: argparse.Namespace, *, sandbox_id: str | None | object = _USE_ARG_SANDBOX_ID) -> Sandbox:
    """Create a sandbox from parsed CLI flags."""
    effective_sandbox_id = cast(str | None, args.sandbox_id if sandbox_id is _USE_ARG_SANDBOX_ID else sandbox_id)
    if effective_sandbox_id is not None and args.sandbox_name:
        raise argparse.ArgumentTypeError("--sandbox-id cannot be combined with --sandbox-name")
    if effective_sandbox_id is not None:
        attach_kwargs: dict[str, object] = {
            "app_name": args.app_name,
            "workspace": args.workspace,
            "command_timeout": args.timeout,
            "sandbox_timeout": args.sandbox_timeout,
            "max_output_bytes": args.max_output_bytes,
            "sandbox_id": effective_sandbox_id,
        }
        volumes = _volumes_from_args(args)
        if volumes:
            attach_kwargs["volumes"] = volumes
        return Sandbox.create(**cast(Any, attach_kwargs))
    if args.sandbox_name:
        attach_kwargs = {
            "app_name": args.app_name,
            "workspace": args.workspace,
            "command_timeout": args.timeout,
            "sandbox_timeout": args.sandbox_timeout,
            "max_output_bytes": args.max_output_bytes,
        }
        volumes = _volumes_from_args(args)
        if volumes:
            attach_kwargs["volumes"] = volumes
        return Sandbox.from_name(args.sandbox_name, **cast(Any, attach_kwargs))
    if args.block_network and (args.allow_domain or args.allow_cidr or args.allow_inbound_cidr):
        raise argparse.ArgumentTypeError(
            "--block-network cannot be combined with --allow-domain, --allow-cidr, or --allow-inbound-cidr"
        )
    create_kwargs: dict[str, object] = {
        "app_name": args.app_name,
        "workspace": args.workspace,
        "image": _resolve_cli_image(args.image),
        "runtime": args.runtime,
        "volumes": _volumes_from_args(args),
        "env": _parse_env(args.env) if args.env else None,
        "command_timeout": args.timeout,
        "sandbox_timeout": args.sandbox_timeout,
        "cpu": args.cpu,
        "memory": args.memory,
        "gpu": args.gpu,
        "region": args.region,
        "block_network": args.block_network,
        "max_output_bytes": args.max_output_bytes,
        "encrypted_ports": tuple(args.encrypted_port),
        "unencrypted_ports": tuple(args.unencrypted_port),
        "readiness_probe": _readiness_probe_from_args(args),
        "sandbox_id": None,
    }
    if args.name:
        create_kwargs["name"] = args.name
    if args.tag:
        create_kwargs["tags"] = dict(args.tag)
    if args.allow_domain:
        create_kwargs["outbound_domain_allowlist"] = tuple(args.allow_domain)
    if args.allow_cidr:
        create_kwargs["outbound_cidr_allowlist"] = tuple(args.allow_cidr)
    if args.allow_inbound_cidr:
        create_kwargs["inbound_cidr_allowlist"] = tuple(args.allow_inbound_cidr)
    return Sandbox.create(**cast(Any, create_kwargs))


def _print_json(payload: Any, *, file: Any = None) -> None:
    """Print a JSON response for shell-friendly CLI output."""
    print(json.dumps(payload, indent=2), file=file or sys.stdout)


def _error_payload(error_type: str, message: str, exit_code: int) -> dict[str, object]:
    """Build the standard JSON error envelope.

    Args:
        error_type: Stable machine-readable error category.
        message: Human-readable error detail.
        exit_code: Process exit code that will be used.

    Returns:
        JSON-serializable error payload.
    """
    return {
        "status": "error",
        "error": {
            "type": error_type,
            "message": message,
            "exit_code": exit_code,
            "next_steps": DEFAULT_ERROR_NEXT_STEPS,
        },
    }


def _exit_with_error(parser: argparse.ArgumentParser, error_type: str, message: str, exit_code: int) -> NoReturn:
    """Print a JSON error envelope and terminate argparse.

    Args:
        parser: Parser used to perform the exit.
        error_type: Stable machine-readable error category.
        message: Human-readable error detail.
        exit_code: Process exit code.

    Raises:
        SystemExit: Always raised by `parser.exit`.
    """
    _print_json(_error_payload(error_type, message, exit_code), file=sys.stderr)
    parser.exit(exit_code)


class JsonArgumentParser(argparse.ArgumentParser):
    """Argument parser that keeps failures machine-readable."""

    def error(self, message: str) -> None:
        """Report argument errors as JSON instead of argparse text.

        Args:
            message: Argument parsing error produced by argparse.

        Raises:
            SystemExit: Always raised with exit code 2.
        """
        _exit_with_error(self, "argument_error", message, 2)


def _require_sandbox_id(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    """Resolve a sandbox ID from positional or global CLI arguments.

    Args:
        args: Parsed CLI namespace.
        parser: Parser used to report argument errors.

    Returns:
        Sandbox ID to operate on.

    Raises:
        SystemExit: If no ID is provided or positional/global IDs disagree.
    """
    positional_id = getattr(args, "target_sandbox_id", None)
    global_id = args.sandbox_id
    if positional_id and global_id and positional_id != global_id:
        parser.error("sandbox id mismatch between positional argument and --sandbox-id")
    sandbox_id = positional_id or global_id
    if not sandbox_id:
        parser.error("sandbox id required as an argument or with --sandbox-id")
    return sandbox_id


def _preflight_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Reject invalid lifecycle combinations before creating Modal resources."""
    if args.sandbox_id and args.sandbox_name:
        parser.error("--sandbox-id cannot be used with --sandbox-name")
    if args.name and args.sandbox_name:
        parser.error("--name cannot be used with --sandbox-name")
    if getattr(args, "target_sandbox_id", None) and args.sandbox_name:
        parser.error("sandbox id argument cannot be used with --sandbox-name")
    readiness_requested = args.readiness_tcp is not None or args.readiness_exec is not None
    if readiness_requested and (args.sandbox_id or args.sandbox_name):
        parser.error("readiness probe flags only apply when creating a sandbox")
    if args.wait_ready and not readiness_requested and not (args.sandbox_id or args.sandbox_name):
        parser.error("--wait-ready requires --readiness-tcp, --readiness-exec, --sandbox-id, or --sandbox-name")
    if args.command_name == "wait-ready" and args.wait_ready:
        parser.error("--wait-ready cannot be combined with wait-ready")
    if args.command_name == "wait-ready" and readiness_requested:
        parser.error("readiness probe flags cannot be combined with wait-ready")
    if args.command_name == "wait-ready" and not (args.sandbox_id or args.sandbox_name):
        parser.error("wait-ready requires --sandbox-id or --sandbox-name")
    if args.command_name == "quickstart" and not args.run and (readiness_requested or args.wait_ready):
        parser.error("readiness flags require quickstart --run or an operational command")
    if args.command_name == "snapshot" and not args.workspace_volume:
        parser.error("snapshot requires --workspace-volume")
    if args.command_name == "sync" and not args.workspace_volume:
        parser.error("sync requires --workspace-volume")
    if args.command_name == "domain" and not (args.sandbox_id or args.sandbox_name):
        parser.error("domain requires --sandbox-id or --sandbox-name from a started sandbox")
    if args.command_name == "quickstart" and args.run and (args.sandbox_id or args.sandbox_name):
        parser.error("--sandbox-id and --sandbox-name cannot be used with quickstart --run")
    if args.command_name == "start" and args.sandbox_id:
        parser.error("--sandbox-id cannot be used with start")
    if args.command_name == "start" and args.sandbox_name:
        parser.error("--sandbox-name cannot be used with start")


def _start_payload(sandbox: Sandbox) -> dict[str, object]:
    """Build JSON output for a newly started long-lived sandbox.

    Args:
        sandbox: Created sandbox that should expose a provider ID.

    Returns:
        JSON-serializable start payload with reuse and stop commands.

    Raises:
        RuntimeError: If Modal did not expose a sandbox ID.
    """
    sandbox_id = sandbox.sandbox_id
    if not sandbox_id:
        raise RuntimeError("Modal did not return a sandbox id.")
    payload = {
        "sandbox_id": sandbox_id,
        "status": "started",
        "workspace": sandbox.config.workspace,
        "sandbox_timeout": sandbox.config.sandbox_timeout,
        "use_command": (
            f'sandbox --sandbox-name {sandbox.config.name} run "python --version"'
            if sandbox.config.name
            else f'sandbox --sandbox-id {sandbox_id} run "python --version"'
        ),
        "stop_command": f"sandbox --sandbox-name {sandbox.config.name} stop"
        if sandbox.config.name
        else f"sandbox stop {sandbox_id}",
    }
    if sandbox.config.name:
        payload["sandbox_name"] = sandbox.config.name
    return payload


def _command_exit_code(result: Any) -> int:
    """Convert a command result into a CLI process exit code.

    Args:
        result: Command-like object with `exit_code` and `timed_out`.

    Returns:
        Sandbox command exit code, 124 for timeout, or 1 for unavailable exit
        status.
    """
    if result.exit_code is not None:
        return result.exit_code
    return 124 if result.timed_out else 1


def _package_version() -> str:
    """Return the installed package version used by CLI metadata.

    Returns:
        Installed distribution version, or the local development fallback.
    """
    try:
        return metadata.version("modal-sandbox-sdk")
    except metadata.PackageNotFoundError:
        return "dev"


def _modal_package_info() -> dict[str, object]:
    """Inspect whether the Modal Python package is importable.

    Returns:
        JSON-serializable package status and version.
    """
    try:
        import modal
    except ImportError:
        return {"installed": False, "version": None}

    return {"installed": True, "version": getattr(modal, "__version__", None)}


def _modal_config_path() -> Path:
    """Return the default Modal config path checked by `doctor`."""
    return Path.home() / ".modal.toml"


def _write_modal_toml(config_path: Path, profile: str, token_id: str, token_secret: str, *, force: bool) -> None:
    """Write a Modal credential profile to the toml config file.

    Reads any existing profiles first so other sections are preserved.
    Non-string values already in the file are written back with repr().

    Raises:
        ValueError: When the profile already exists and force is False.
    """
    existing: dict[str, dict[str, object]] = {}
    if config_path.exists():
        with config_path.open("rb") as f:
            existing = tomllib.load(f)

    if profile in existing and not force:
        raise ValueError(f"Profile {profile!r} already exists in {config_path}. Use --force to overwrite.")

    if profile in existing:
        existing[profile]["token_id"] = token_id
        existing[profile]["token_secret"] = token_secret
    else:
        existing[profile] = {"token_id": token_id, "token_secret": token_secret}

    lines: list[str] = []
    for section, values in existing.items():
        lines.append(f"[{section}]")
        for key, val in values.items():
            lines.append(f'{key} = "{val}"' if isinstance(val, str) else f"{key} = {val!r}")
        lines.append("")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("\n".join(lines), encoding="utf-8")


def _credential_status() -> dict[str, object]:
    """Inspect local Modal credential signals without contacting Modal.

    Returns:
        JSON-serializable credential status from environment and config file
        presence.
    """
    env_has_id = bool(os.environ.get("MODAL_TOKEN_ID"))
    env_has_secret = bool(os.environ.get("MODAL_TOKEN_SECRET"))
    config_path = _modal_config_path()
    config_exists = config_path.exists()
    has_complete_env = env_has_id and env_has_secret

    if has_complete_env:
        status = "configured_from_environment"
    elif env_has_id or env_has_secret:
        status = "partial_environment"
    elif config_exists:
        status = "configured_from_modal_toml"
    else:
        status = "missing_or_unknown"

    return {
        "status": status,
        "authenticated": status in {"configured_from_environment", "configured_from_modal_toml"},
        "environment": {
            "modal_token_id_set": env_has_id,
            "modal_token_secret_set": env_has_secret,
            "environment_vars_set": has_complete_env,
        },
        "modal_toml": {
            "path": str(config_path),
            "exists": config_exists,
        },
        "modal_profile": os.environ.get("MODAL_PROFILE"),
    }


def _recommended_setup_command() -> str:
    """Return the setup command shown in local-development guidance."""
    return "uv run modal setup"


def _readiness(modal_package: dict[str, object], credentials: dict[str, object]) -> dict[str, object]:
    """Summarize whether the local environment looks ready for live sandboxes.

    Args:
        modal_package: Result from `_modal_package_info`.
        credentials: Result from `_credential_status`.

    Returns:
        JSON-serializable readiness status, problems, and next steps.
    """
    problems: list[str] = []
    next_steps: list[str] = []

    if not modal_package["installed"]:
        problems.append("modal_package_not_installed")
        next_steps.append("Install dependencies with `uv sync`.")

    if credentials["status"] == "partial_environment":
        problems.append("modal_credentials_partial_environment")
        next_steps.append("Set both `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`, or run `uv run modal setup`.")
    elif credentials["status"] == "missing_or_unknown":
        problems.append("modal_credentials_missing")
        next_steps.append(f"Run `{_recommended_setup_command()}` before creating a live sandbox.")

    ready = not problems
    if ready:
        next_steps.append("Run `sandbox quickstart --run` to create a short-lived sandbox and verify execution.")

    return {
        "ready": ready,
        "status": "ready" if ready else "needs_setup",
        "problems": problems,
        "next_steps": next_steps,
    }


def _safe_quickstart_commands() -> list[str]:
    """Return recommended commands that do not create Modal resources."""
    return [command["command"] for command in RECOMMENDED_FIRST_COMMANDS if command["creates_modal_resources"] is False]


def _live_quickstart_command() -> str:
    """Return the first live Modal verification command."""
    return "sandbox quickstart --run"


def _dry_command_names() -> list[str]:
    """Return dry command names that never create Modal resources."""
    return ["dry", "schema", "doctor", "quickstart"]


def _schema_payload() -> dict[str, object]:
    """Build the machine-readable CLI contract.

    Returns:
        JSON-serializable schema containing command metadata, lifecycle notes,
        auth guidance, image aliases, and golden workflows.
    """
    return {
        "name": "sandbox",
        "package": "modal-sandbox-sdk",
        "version": _package_version(),
        "schema_version": CLI_SCHEMA_VERSION,
        "description": "CLI for running commands and file workflows inside Modal Sandboxes.",
        "default_output": "json",
        "global_options": {
            "--app-name": "Modal app name used for sandbox creation.",
            "--name": "Name assigned to a newly created sandbox. Unique within the app while running.",
            "--tag KEY=VALUE": "Tag assigned to a newly created sandbox. Repeatable.",
            "--workspace": "Default sandbox directory for relative paths.",
            "--image": "Registry image tag or supported alias passed to Modal.",
            "--runtime": "Vercel-style runtime alias. Supported values: python3.13, node24, node22.",
            "--workspace-volume": "Modal volume name mounted at the workspace path.",
            "--volume NAME:/mount": "Modal volume name and absolute sandbox mount path. Repeatable.",
            "--env KEY=VALUE": "Environment variable passed to the sandbox. Repeatable.",
            "--timeout": "Command timeout in seconds for run.",
            "--sandbox-timeout": "Modal sandbox lifetime timeout in seconds.",
            "--cpu": "CPU request passed through to Modal.",
            "--memory": "Memory request in MiB passed through to Modal.",
            "--gpu": "GPU request passed through to Modal.",
            "--region": "Region preference passed through to Modal.",
            "--block-network": "Block outbound network access from the sandbox.",
            "--allow-domain DOMAIN": "Allow sandbox outbound network access to a domain. Repeatable.",
            "--allow-cidr CIDR": "Allow sandbox outbound network access to a CIDR range. Repeatable.",
            "--allow-inbound-cidr CIDR": "Allow inbound tunnel/connect-token access from a CIDR range. Repeatable.",
            "--sandbox-id": "Attach to an existing Modal sandbox by ID instead of creating one.",
            "--sandbox-name": "Attach to an existing running Modal sandbox by name instead of creating one.",
            "--max-output-bytes": "Maximum captured bytes for stdout and stderr separately. Defaults to 10485760; use 0 to capture no bytes.",
            "--encrypted-port": "Expose an HTTPS Modal tunnel for the given port. Repeatable.",
            "--unencrypted-port": "Expose a TCP Modal tunnel for the given port. Repeatable.",
            "--readiness-tcp PORT": "Create a sandbox with a Modal TCP readiness probe.",
            "--readiness-exec COMMAND": "Create a sandbox with a Modal exec readiness probe parsed into argv.",
            "--readiness-interval-ms": "Readiness probe polling interval in milliseconds. Defaults to 100.",
            "--wait-ready": "Wait for readiness before running an operational command.",
            "--ready-timeout": "Maximum seconds to wait when --wait-ready is used. Defaults to 300.",
        },
        "path_rules": PATH_RULES,
        "lifecycle": {
            "creates_or_attaches_per_command": True,
            "dry_commands": _dry_command_names(),
            "safe_discovery_commands": _dry_command_names(),
            "live_modal_commands": LIVE_MODAL_COMMANDS,
            "long_lived_cli_workflow": "Use start to create a sandbox, --sandbox-id to reuse it, and stop to terminate it.",
            "named_sandboxes": "Use --name NAME when starting a sandbox and --sandbox-name NAME to attach to the currently running named sandbox.",
            "created_sandboxes_close_behavior": "terminate",
            "attached_sandboxes_close_behavior": "detach",
            "persistent_files": "Use --workspace-volume to preserve files across separate CLI commands.",
            "volume_mounts": "Use --volume NAME:/mount to mount additional Modal volumes at absolute sandbox paths.",
            "domain_allowlist": "Use --allow-domain DOMAIN to restrict sandbox outbound network access to listed domains.",
            "cidr_allowlists": "Use --allow-cidr CIDR for outbound IP ranges and --allow-inbound-cidr CIDR for inbound tunnel/connect-token ranges.",
            "preflight_validation": "Invalid lifecycle combinations and global configuration are rejected before sandbox creation.",
        },
        "auth": {
            "requires_modal_credentials": True,
            "setup_commands": SETUP_COMMANDS,
            "environment_variables": ["MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "MODAL_PROFILE"],
            "token_acquisition": {
                "url": "https://modal.com/settings/tokens",
                "description": (
                    "Create a token at the Modal dashboard, then set MODAL_TOKEN_ID and "
                    "MODAL_TOKEN_SECRET for non-interactive use, or run "
                    "`sandbox auth --token-id ID --token-secret SECRET` to write ~/.modal.toml."
                ),
                "non_interactive_command": "sandbox auth --token-id YOUR_TOKEN_ID --token-secret YOUR_TOKEN_SECRET",
            },
        },
        "image_aliases": IMAGE_ALIASES,
        "recommended_first_commands": RECOMMENDED_FIRST_COMMANDS,
        "golden_workflows": GOLDEN_WORKFLOWS,
        "commands": COMMANDS_SCHEMA,
    }


def _agent_manifest_payload() -> dict[str, object]:
    """Build a compact low-token manifest for coding agents.

    Returns:
        JSON-serializable agent orientation data. This intentionally omits the
        full command schema; agents can call `sandbox schema` when they need
        command-level detail.
    """
    return {
        "name": "sandbox-agent-manifest",
        "package": "modal-sandbox-sdk",
        "version": _package_version(),
        "schema_version": CLI_SCHEMA_VERSION,
        "description": "Low-token orientation manifest for the modal-sandbox plugin and its SDK/CLI engine.",
        "product_boundary": [
            "Codex plugin and end-user skill backed by a small Python SDK and JSON-first CLI.",
            "The plugin requires the installed sandbox CLI and does not duplicate it or add MCP.",
            "Not a generic sandbox platform or replacement for Modal's full SDK.",
            "Keep Modal imported lazily and default validation resource-free.",
        ],
        "read_order": [
            "AGENTS.md",
            "ARCHITECTURE.md",
            "docs/PRODUCT_SENSE.md",
            "docs/references/cli.md",
            "docs/exec-plans/index.md",
        ],
        "skills": AGENT_SKILLS,
        "safe_discovery": {
            "creates_modal_resources": False,
            "commands": [
                "sandbox dry",
                "sandbox schema --agent",
                "sandbox schema",
                "sandbox doctor",
                "sandbox quickstart",
            ],
        },
        "live_modal": {
            "requires_explicit_user_request": True,
            "opt_in_test_command": "MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 ./scripts/dev/live-smoke.sh",
            "commands": LIVE_MODAL_COMMANDS,
        },
        "golden_workflows": GOLDEN_WORKFLOWS,
        "path_rules": PATH_RULES,
        "validation": {
            "quick_no_resource": "./scripts/dev/quickstart.sh",
            "full_no_resource": "./scripts/dev/check.sh",
            "schema_codegen": "./scripts/dev/schema.sh",
            "exec_plan_state": "./scripts/execplan/check.sh",
            "live_modal": "MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 ./scripts/dev/live-smoke.sh",
        },
        "planning": {
            "index": "docs/exec-plans/index.md",
            "active_plan_rule": "If active initiatives exist, read their PLAN file and JSON/JSONL state before editing.",
            "completed_plan_rule": "Do not read completed plan state unless doing archaeology or release retrospective work.",
        },
        "docs": {
            "agent_notes": "docs/references/agents.md",
            "new_agent_prompt": "docs/references/new-agent-prompt.md",
            "cli_reference": "docs/references/cli.md",
            "quality": "docs/QUALITY_SCORE.md",
            "reliability": "docs/RELIABILITY.md",
            "security": "docs/SECURITY.md",
        },
    }


def _dry_payload() -> dict[str, object]:
    """Build safe-discovery command metadata without creating resources."""
    modal_package = _modal_package_info()
    credentials = _credential_status()
    readiness = _readiness(modal_package, credentials)
    return {
        "status": "ready_to_run" if readiness["ready"] else "needs_setup",
        "creates_modal_resources": False,
        "dry_commands": _dry_command_names(),
        "safe_commands": _safe_quickstart_commands(),
        "recommended_next_command": "sandbox quickstart",
        "live_command": _live_quickstart_command(),
        "checks": {
            "ready": readiness["ready"],
            "modal_package": modal_package,
            "credentials": credentials,
            "problems": readiness["problems"],
        },
        "next_steps": readiness["next_steps"],
    }


def _doctor_payload() -> dict[str, object]:
    """Build local Modal readiness diagnostics without creating resources.

    Returns:
        JSON-serializable doctor payload.
    """
    modal_package = _modal_package_info()
    credentials = _credential_status()
    readiness = _readiness(modal_package, credentials)
    recommended_commands = [*RECOMMENDED_FIRST_COMMANDS]
    if credentials["status"] in {"missing_or_unknown", "partial_environment"}:
        recommended_commands.append(
            {
                "command": _recommended_setup_command(),
                "creates_modal_resources": False,
                "purpose": "Sign in to Modal when credentials are missing or incomplete.",
            }
        )
    if credentials["status"] == "partial_environment":
        ready_hint = (
            "Modal token environment variables are incomplete. Set both token variables before creating a sandbox."
        )
    elif credentials["status"] == "missing_or_unknown":
        ready_hint = "Modal credentials were not found. Run modal setup before creating a sandbox."
    else:
        ready_hint = "Modal credentials appear to be configured."

    if readiness["ready"]:
        summary = {
            "ready": True,
            "message": "Modal is configured. You can run a live sandbox quickstart.",
            "next_command": "sandbox quickstart --run",
        }
    else:
        next_command = _recommended_setup_command()
        if credentials["status"] == "partial_environment":
            next_command = "Set both MODAL_TOKEN_ID and MODAL_TOKEN_SECRET"
        summary = {
            "ready": False,
            "message": ready_hint,
            "next_command": next_command,
        }

    return {
        **readiness,
        "modal_package": modal_package,
        "credentials": credentials,
        "ready_hint": ready_hint,
        "recommended_commands": recommended_commands,
        "setup_commands": SETUP_COMMANDS,
        "creates_modal_resources": False,
        "next_safe_command": "sandbox quickstart",
        "summary": summary,
    }


def _quickstart_payload(*, creates_modal_resources: bool) -> dict[str, object]:
    """Build quickstart preview or live-run metadata.

    Args:
        creates_modal_resources: Whether the surrounding command creates a live
            Modal sandbox.

    Returns:
        JSON-serializable quickstart payload.
    """
    modal_package = _modal_package_info()
    credentials = _credential_status()
    readiness = _readiness(modal_package, credentials)
    live_command = _live_quickstart_command()
    return {
        "status": "ready_to_run" if readiness["ready"] else "needs_setup",
        "creates_modal_resources": creates_modal_resources,
        "checks": {
            "ready": readiness["ready"],
            "modal_package": modal_package,
            "credentials": credentials,
            "problems": readiness["problems"],
        },
        "next_steps": readiness["next_steps"],
        "safe_commands": _safe_quickstart_commands(),
        "live_command": live_command,
        "quickstart_command": QUICKSTART_COMMAND,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Parser configured with global sandbox creation flags and operational
        subcommands.
    """
    parser = JsonArgumentParser(
        prog="sandbox",
        description=(
            "Run commands and file workflows inside Modal Sandboxes. "
            "Operational commands print JSON. Discovery commands do not create Modal resources."
        ),
        epilog=(
            "Machine-readable discovery:\n"
            "  sandbox dry               List safe discovery commands as JSON.\n"
            "  sandbox schema            Print command metadata, output shapes, and examples as JSON.\n"
            "  sandbox doctor            Inspect local Modal setup without creating a sandbox.\n"
            "  sandbox quickstart        Preview the first live sandbox command as JSON.\n"
            "  sandbox --image ... start Create a reusable sandbox and print its ID.\n\n"
            "First time using Modal? Run `modal setup` to sign in. "
            "For headless environments, set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # These flags intentionally mirror the ergonomic SDK creation options so
    # shell usage and Python usage teach the same mental model.
    parser.add_argument("--app-name", default="modal-sandbox-sdk")
    parser.add_argument("--name", type=_sandbox_name, help="Name for a newly created sandbox.")
    parser.add_argument("--tag", type=_parse_tag, action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--workspace", type=_absolute_sandbox_path, default="/workspace")
    parser.add_argument("--image", help="Registry image tag or alias such as py313, py312, py311, or ubuntu24.")
    parser.add_argument(
        "--runtime", choices=["python3.13", "node24", "node22"], help="Runtime alias such as python3.13."
    )
    parser.add_argument("--workspace-volume", type=_non_empty_value)
    parser.add_argument("--volume", type=_parse_volume, action="append", default=[], metavar="NAME:/MOUNT")
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--timeout", type=_positive_int, default=30)
    parser.add_argument("--sandbox-timeout", type=_positive_int, default=300)
    parser.add_argument("--cpu", type=_positive_float)
    parser.add_argument("--memory", type=_positive_int)
    parser.add_argument("--gpu")
    parser.add_argument("--region")
    parser.add_argument("--block-network", action="store_true")
    parser.add_argument("--allow-domain", type=_domain_allowlist_value, action="append", default=[], metavar="DOMAIN")
    parser.add_argument("--allow-cidr", type=_cidr_allowlist_value, action="append", default=[], metavar="CIDR")
    parser.add_argument("--allow-inbound-cidr", type=_cidr_allowlist_value, action="append", default=[], metavar="CIDR")
    parser.add_argument("--sandbox-id")
    parser.add_argument("--sandbox-name", type=_sandbox_name)
    parser.add_argument("--max-output-bytes", type=_non_negative_int, default=10 * 1024 * 1024)
    parser.add_argument("--encrypted-port", type=_port, action="append", default=[], metavar="PORT")
    parser.add_argument("--unencrypted-port", type=_port, action="append", default=[], metavar="PORT")
    readiness_group = parser.add_mutually_exclusive_group()
    readiness_group.add_argument(
        "--readiness-tcp",
        type=_port,
        metavar="PORT",
        help="Create the sandbox with a TCP readiness probe for PORT.",
    )
    readiness_group.add_argument(
        "--readiness-exec",
        type=_readiness_exec,
        metavar="COMMAND",
        help="Create the sandbox with an argv-style readiness command parsed from COMMAND.",
    )
    parser.add_argument(
        "--readiness-interval-ms",
        type=_positive_int,
        default=100,
        help="Readiness probe polling interval in milliseconds.",
    )
    parser.add_argument(
        "--wait-ready",
        action="store_true",
        help="Wait for the sandbox readiness probe before running the command.",
    )
    parser.add_argument("--ready-timeout", type=_positive_int, default=300)
    parser.add_argument(
        "--dry",
        action="store_true",
        help="List safe discovery commands without creating Modal resources.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")

    subparsers = parser.add_subparsers(dest="command_name", parser_class=JsonArgumentParser)

    subparsers.add_parser("start", help="Create a sandbox, print its ID, and leave it running.")

    stop_parser = subparsers.add_parser("stop", help="Terminate a running sandbox by ID.")
    stop_parser.add_argument("target_sandbox_id", nargs="?")

    run_parser = subparsers.add_parser("run", help="Run a command inside the sandbox.")
    run_parser.add_argument(
        "--cwd", help="Working directory inside the sandbox. Relative paths resolve inside the workspace."
    )
    run_parser.add_argument(
        "--use-command-exit-code",
        action="store_true",
        help="Exit with the sandbox command's exit code instead of 0.",
    )
    run_parser.add_argument("command")

    run_command_parser = subparsers.add_parser("run-command", help="Run an argv-style command inside the sandbox.")
    run_command_parser.add_argument(
        "--cwd", help="Working directory inside the sandbox. Relative paths resolve inside the workspace."
    )
    run_command_parser.add_argument("--env", action="append", default=[], dest="command_env", metavar="KEY=VALUE")
    run_command_parser.add_argument(
        "--use-command-exit-code",
        action="store_true",
        help="Exit with the sandbox command's exit code instead of 0.",
    )
    run_command_parser.add_argument("cmd")
    run_command_parser.add_argument("args", nargs=argparse.REMAINDER)

    write_parser = subparsers.add_parser("write", help="Write a file inside the sandbox workspace.")
    write_parser.add_argument("path")
    write_input = write_parser.add_mutually_exclusive_group(required=True)
    write_input.add_argument("--content", help="Inline UTF-8 text content to write.")
    write_input.add_argument("--content-file", help="Local UTF-8 text file to read and write.")
    write_input.add_argument("--stdin", action="store_true", dest="read_stdin", help="Read UTF-8 text from stdin.")
    write_input.add_argument("--binary-file", metavar="PATH", help="Local binary file to read and write as bytes.")
    write_input.add_argument(
        "--binary-stdin",
        action="store_true",
        dest="binary_stdin",
        help="Read raw bytes from stdin and write as binary.",
    )

    read_parser = subparsers.add_parser("read", help="Read a text file inside the sandbox workspace.")
    read_parser.add_argument("path")

    ls_parser = subparsers.add_parser("ls", help="List files inside the sandbox workspace.")
    ls_parser.add_argument("path", nargs="?", default=".")

    mkdir_parser = subparsers.add_parser("mkdir", help="Create a directory inside the sandbox workspace.")
    mkdir_parser.add_argument("path")
    mkdir_parser.add_argument("--no-parents", action="store_true", help="Do not create missing parent directories.")

    rm_parser = subparsers.add_parser("rm", help="Remove a file or directory inside the sandbox workspace.")
    rm_parser.add_argument("path")
    rm_parser.add_argument("-r", "--recursive", action="store_true", help="Remove directories recursively.")

    upload_parser = subparsers.add_parser("upload", help="Copy a local file or directory into the sandbox.")
    upload_parser.add_argument("local_path")
    upload_parser.add_argument("remote_path")

    download_parser = subparsers.add_parser("download", help="Copy a sandbox file or directory to the local machine.")
    download_parser.add_argument("remote_path")
    download_parser.add_argument("local_path")

    domain_parser = subparsers.add_parser("domain", help="Print the public URL for a declared sandbox port.")
    domain_parser.add_argument("port", type=_positive_int)

    wait_ready_parser = subparsers.add_parser("wait-ready", help="Wait for an existing sandbox readiness probe.")
    wait_ready_parser.add_argument("--timeout", type=_positive_int, default=300, dest="wait_ready_timeout")

    subparsers.add_parser("snapshot", help="Create a volume-backed workspace snapshot checkpoint.")

    snapshot_filesystem_parser = subparsers.add_parser(
        "snapshot-filesystem", help="Create a Modal-native filesystem image snapshot."
    )
    snapshot_filesystem_parser.add_argument("--timeout", type=_positive_int, default=55, dest="snapshot_timeout")
    snapshot_filesystem_ttl = snapshot_filesystem_parser.add_mutually_exclusive_group()
    snapshot_filesystem_ttl.add_argument("--ttl", type=_non_negative_int, default=30 * 24 * 3600)
    snapshot_filesystem_ttl.add_argument("--no-ttl", action="store_true")

    snapshot_directory_parser = subparsers.add_parser(
        "snapshot-directory", help="Create a Modal-native directory image snapshot."
    )
    snapshot_directory_parser.add_argument("path")
    snapshot_directory_parser.add_argument("--timeout", type=_positive_int, default=55, dest="snapshot_timeout")
    snapshot_directory_ttl = snapshot_directory_parser.add_mutually_exclusive_group()
    snapshot_directory_ttl.add_argument("--ttl", type=_non_negative_int, default=30 * 24 * 3600)
    snapshot_directory_ttl.add_argument("--no-ttl", action="store_true")

    mount_image_parser = subparsers.add_parser("mount-image", help="Mount a Modal image snapshot in the sandbox.")
    mount_image_parser.add_argument("path")
    mount_image_parser.add_argument("image_id")

    unmount_image_parser = subparsers.add_parser("unmount-image", help="Unmount a Modal image snapshot.")
    unmount_image_parser.add_argument("path")

    stat_parser = subparsers.add_parser("stat", help="Return metadata for a sandbox path.")
    stat_parser.add_argument("path")

    watch_parser = subparsers.add_parser("watch", help="Watch a sandbox path for a bounded time.")
    watch_parser.add_argument("path")
    watch_parser.add_argument("--timeout", type=_positive_int, required=True, dest="watch_timeout")
    watch_parser.add_argument("--recursive", action="store_true")
    watch_parser.add_argument("--event", type=_watch_event, action="append", default=[], dest="watch_events")

    subparsers.add_parser("sync", help="Persist workspace-volume changes immediately.")

    seed_git_parser = subparsers.add_parser("seed-git", help="Clone a public Git repository into the sandbox.")
    seed_git_parser.add_argument("url", type=_public_http_url)
    seed_git_parser.add_argument("--dest", default=".")
    seed_git_parser.add_argument("--ref")
    seed_git_parser.add_argument("--depth", type=_non_negative_int, default=1)

    seed_tarball_parser = subparsers.add_parser("seed-tarball", help="Extract a public tarball into the sandbox.")
    seed_tarball_parser.add_argument("url", type=_public_http_url)
    seed_tarball_parser.add_argument("--dest", default=".")
    seed_tarball_parser.add_argument("--strip-components", type=_non_negative_int, default=1)

    auth_parser = subparsers.add_parser(
        "auth", help="Write Modal credentials to ~/.modal.toml for non-interactive use."
    )
    auth_parser.add_argument("--token-id", required=True, dest="token_id", help="Modal token ID.")
    auth_parser.add_argument("--token-secret", required=True, dest="token_secret", help="Modal token secret.")
    auth_parser.add_argument("--profile", default="default", help="Modal config profile to write (default: 'default').")
    auth_parser.add_argument("--force", action="store_true", help="Overwrite an existing profile entry.")

    subparsers.add_parser("dry", help="List safe discovery commands that do not create Modal resources.")

    schema_parser = subparsers.add_parser("schema", help="Print a machine-readable CLI schema.")
    schema_parser.add_argument(
        "--agent",
        action="store_true",
        help="Print a compact low-token agent manifest instead of the full CLI schema.",
    )

    subparsers.add_parser("doctor", help="Inspect local Modal setup without creating a sandbox.")

    quickstart_parser = subparsers.add_parser("quickstart", help="Preview or run the beginner quickstart.")
    quickstart_parser.add_argument(
        "--run",
        action="store_true",
        help="Create a short-lived sandbox and run the quickstart command.",
    )

    return parser


def _write_content_from_args(args: argparse.Namespace) -> str | bytes:
    if getattr(args, "binary_stdin", False):
        return sys.stdin.buffer.read()
    if getattr(args, "binary_file", None):
        return Path(args.binary_file).read_bytes()
    if args.content is not None:
        return args.content
    if args.content_file is not None:
        return Path(args.content_file).read_text(encoding="utf-8")
    if args.read_stdin:
        return sys.stdin.read()
    raise argparse.ArgumentTypeError(
        "write requires --content, --content-file, --stdin, --binary-file, or --binary-stdin"
    )


def _snapshot_ttl_from_args(args: argparse.Namespace) -> int | None:
    return None if getattr(args, "no_ttl", False) else args.ttl


# ---------------------------------------------------------------------------
# Per-command handler functions
# Each receives (args, sandbox) and returns an int exit code (0 for success).
# ---------------------------------------------------------------------------


def _cmd_wait_ready(args: argparse.Namespace, sandbox: Sandbox) -> int:
    sandbox.wait_until_ready(timeout=args.wait_ready_timeout)
    payload: dict[str, object] = {
        "sandbox_id": sandbox.sandbox_id,
        "status": "ready",
        "timeout": args.wait_ready_timeout,
    }
    if args.sandbox_name:
        payload["sandbox_name"] = args.sandbox_name
    _print_json(payload)
    return 0


def _cmd_run(args: argparse.Namespace, sandbox: Sandbox) -> int:
    result = sandbox.run(args.command, cwd=args.cwd, max_output_bytes=args.max_output_bytes)
    _print_json(result.to_dict())
    return _command_exit_code(result) if args.use_command_exit_code else 0


def _cmd_run_command(args: argparse.Namespace, sandbox: Sandbox) -> int:
    result = sandbox.run_command(
        args.cmd,
        args.args,
        cwd=args.cwd,
        env=_parse_env(args.command_env) if args.command_env else None,
        max_output_bytes=args.max_output_bytes,
    )
    _print_json(result.to_dict())
    return _command_exit_code(result) if args.use_command_exit_code else 0


def _cmd_write(args: argparse.Namespace, sandbox: Sandbox) -> int:
    content = _write_content_from_args(args)
    if isinstance(content, bytes):
        sandbox.write_bytes(args.path, content)
    else:
        sandbox.write_text(args.path, content)
    _print_json({"path": args.path, "status": "wrote"})
    return 0


def _cmd_read(args: argparse.Namespace, sandbox: Sandbox) -> int:
    _print_json({"path": args.path, "content": sandbox.read_text(args.path)})
    return 0


def _cmd_ls(args: argparse.Namespace, sandbox: Sandbox) -> int:
    _print_json({"path": args.path, "files": sandbox.list_files(args.path)})
    return 0


def _cmd_mkdir(args: argparse.Namespace, sandbox: Sandbox) -> int:
    parents = not args.no_parents
    sandbox.mkdir(args.path, parents=parents)
    _print_json({"parents": parents, "path": args.path, "status": "created"})
    return 0


def _cmd_rm(args: argparse.Namespace, sandbox: Sandbox) -> int:
    sandbox.remove(args.path, recursive=args.recursive)
    _print_json({"path": args.path, "recursive": args.recursive, "status": "removed"})
    return 0


def _cmd_upload(args: argparse.Namespace, sandbox: Sandbox) -> int:
    sandbox.copy_from_local(args.local_path, args.remote_path)
    _print_json({"local_path": args.local_path, "remote_path": args.remote_path, "status": "uploaded"})
    return 0


def _cmd_download(args: argparse.Namespace, sandbox: Sandbox) -> int:
    sandbox.copy_to_local(args.remote_path, args.local_path)
    _print_json({"local_path": args.local_path, "remote_path": args.remote_path, "status": "downloaded"})
    return 0


def _cmd_domain(args: argparse.Namespace, sandbox: Sandbox) -> int:
    _print_json({"port": args.port, "url": sandbox.domain(args.port)})
    return 0


def _cmd_snapshot(args: argparse.Namespace, sandbox: Sandbox) -> int:
    snapshot = sandbox.workspace_checkpoint()
    _print_json({"kind": snapshot.kind, "name": snapshot.name, "status": "created", "workspace": snapshot.workspace})
    return 0


def _cmd_snapshot_filesystem(args: argparse.Namespace, sandbox: Sandbox) -> int:
    snapshot = sandbox.snapshot_filesystem(timeout=args.snapshot_timeout, ttl=_snapshot_ttl_from_args(args))
    payload = snapshot.to_dict()
    payload["status"] = "created"
    _print_json(payload)
    return 0


def _cmd_snapshot_directory(args: argparse.Namespace, sandbox: Sandbox) -> int:
    snapshot = sandbox.snapshot_directory(args.path, timeout=args.snapshot_timeout, ttl=_snapshot_ttl_from_args(args))
    payload = snapshot.to_dict()
    payload["status"] = "created"
    _print_json(payload)
    return 0


def _cmd_mount_image(args: argparse.Namespace, sandbox: Sandbox) -> int:
    sandbox.mount_image(args.path, args.image_id)
    _print_json({"image_id": args.image_id, "path": args.path, "status": "mounted"})
    return 0


def _cmd_unmount_image(args: argparse.Namespace, sandbox: Sandbox) -> int:
    sandbox.unmount_image(args.path)
    _print_json({"path": args.path, "status": "unmounted"})
    return 0


def _cmd_stat(args: argparse.Namespace, sandbox: Sandbox) -> int:
    _print_json(sandbox.stat(args.path).to_dict())
    return 0


def _cmd_watch(args: argparse.Namespace, sandbox: Sandbox) -> int:
    events = sandbox.watch(
        args.path,
        recursive=args.recursive,
        timeout=args.watch_timeout,
        filter=args.watch_events or None,
    )
    _print_json(
        {
            "events": [event.to_dict() for event in events],
            "path": args.path,
            "recursive": args.recursive,
            "timeout": args.watch_timeout,
        }
    )
    return 0


def _cmd_sync(args: argparse.Namespace, sandbox: Sandbox) -> int:
    _print_json(sandbox.sync_workspace().to_dict())
    return 0


def _cmd_seed_git(args: argparse.Namespace, sandbox: Sandbox) -> int:
    _print_json(sandbox.seed_git(args.url, destination=args.dest, ref=args.ref, depth=args.depth).to_dict())
    return 0


def _cmd_seed_tarball(args: argparse.Namespace, sandbox: Sandbox) -> int:
    _print_json(sandbox.seed_tarball(args.url, destination=args.dest, strip_components=args.strip_components).to_dict())
    return 0


_COMMAND_HANDLERS: dict[str, Any] = {
    "wait-ready": _cmd_wait_ready,
    "run": _cmd_run,
    "run-command": _cmd_run_command,
    "write": _cmd_write,
    "read": _cmd_read,
    "ls": _cmd_ls,
    "mkdir": _cmd_mkdir,
    "rm": _cmd_rm,
    "upload": _cmd_upload,
    "download": _cmd_download,
    "domain": _cmd_domain,
    "snapshot": _cmd_snapshot,
    "snapshot-filesystem": _cmd_snapshot_filesystem,
    "snapshot-directory": _cmd_snapshot_directory,
    "mount-image": _cmd_mount_image,
    "unmount-image": _cmd_unmount_image,
    "stat": _cmd_stat,
    "watch": _cmd_watch,
    "sync": _cmd_sync,
    "seed-git": _cmd_seed_git,
    "seed-tarball": _cmd_seed_tarball,
}


def main(argv: list[str] | None = None) -> int:
    """Run the sandbox CLI.

    Args:
        argv: Optional argument list. When omitted, argparse reads `sys.argv`.

    Returns:
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.dry:
        if args.command_name is not None:
            parser.error("--dry cannot be combined with a subcommand; use `sandbox dry`")
        _print_json(_dry_payload())
        return 0
    if args.command_name is None:
        parser.error("a command is required")

    _preflight_args(args, parser)

    if args.command_name == "dry":
        _print_json(_dry_payload())
        return 0
    if args.command_name == "schema":
        _print_json(_agent_manifest_payload() if args.agent else _schema_payload())
        return 0
    if args.command_name == "doctor":
        _print_json(_doctor_payload())
        return 0
    if args.command_name == "quickstart" and not args.run:
        _print_json(_quickstart_payload(creates_modal_resources=False))
        return 0

    if args.command_name == "auth":
        config_path = _modal_config_path()
        try:
            _write_modal_toml(config_path, args.profile, args.token_id, args.token_secret, force=args.force)
        except ValueError as exc:
            _exit_with_error(parser, "auth_error", str(exc), 1)
        _print_json(
            {
                "status": "configured",
                "profile": args.profile,
                "config_path": str(config_path),
                "creates_modal_resources": False,
            }
        )
        return 0

    sandbox: Sandbox | None = None
    try:
        if args.command_name == "quickstart":
            sandbox = _sandbox_from_args(args)
            if args.wait_ready:
                sandbox.wait_until_ready(timeout=args.ready_timeout)
            result = sandbox.run(QUICKSTART_COMMAND)
            payload = result.to_dict()
            payload["creates_modal_resources"] = True
            payload["quickstart"] = _quickstart_payload(creates_modal_resources=True)
            _print_json(payload)
            return 0

        if args.command_name == "start":
            sandbox = _sandbox_from_args(args, sandbox_id=None)
            waited_ready = False
            if args.wait_ready:
                sandbox.wait_until_ready(timeout=args.ready_timeout)
                waited_ready = True
            payload = _start_payload(sandbox)
            if waited_ready:
                payload["ready"] = True
            sandbox.detach()
            sandbox = None
            _print_json(payload)
            return 0

        if args.command_name == "stop":
            sandbox_name = args.sandbox_name
            if sandbox_name:
                sandbox = Sandbox.from_name(
                    sandbox_name,
                    app_name=args.app_name,
                    workspace=args.workspace,
                    command_timeout=args.timeout,
                    sandbox_timeout=args.sandbox_timeout,
                    max_output_bytes=args.max_output_bytes,
                    ensure_workspace=False,
                )
                sandbox_id = sandbox.sandbox_id
            else:
                sandbox_id = _require_sandbox_id(args, parser)
                sandbox = Sandbox.from_id(
                    sandbox_id,
                    app_name=args.app_name,
                    workspace=args.workspace,
                    command_timeout=args.timeout,
                    sandbox_timeout=args.sandbox_timeout,
                    max_output_bytes=args.max_output_bytes,
                    ensure_workspace=False,
                )
            sandbox.terminate(wait=True)
            sandbox = None
            payload: dict[str, object] = {"sandbox_id": sandbox_id, "status": "terminated"}
            if sandbox_name:
                payload["sandbox_name"] = sandbox_name
            _print_json(payload)
            return 0

        sandbox = _sandbox_from_args(args)
        if args.command_name != "wait-ready" and args.wait_ready:
            sandbox.wait_until_ready(timeout=args.ready_timeout)

        handler = _COMMAND_HANDLERS.get(args.command_name)
        if handler is None:
            parser.error(f"Unknown command: {args.command_name}")
        return handler(args, sandbox)

    except argparse.ArgumentTypeError as exc:
        _exit_with_error(parser, "argument_error", str(exc), 2)
    except ModalAuthenticationError as exc:
        _exit_with_error(parser, "modal_authentication_error", str(exc), 1)
    except Exception as exc:
        _exit_with_error(parser, "runtime_error", str(exc), 1)
    finally:
        if sandbox is not None:
            sandbox.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
