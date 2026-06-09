from __future__ import annotations

import argparse
import json
import os
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, NoReturn, cast

from sandbox import Images, ModalAuthenticationError, Sandbox, SandboxVolume

SETUP_COMMANDS = [
    "modal setup",
    "python -m modal setup",
    "modal token new",
    "modal token set --token-id <token id> --token-secret <token secret>",
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
        ],
        "success_signal": "read returns the file content and snapshot names the workspace volume.",
    },
    {
        "id": "long_lived_reuse",
        "purpose": "Reuse one live sandbox for iterative work, then terminate it.",
        "creates_modal_resources": True,
        "commands": [
            "sandbox --image py313 start",
            'sandbox --sandbox-id <sandbox_id> write app.py --content "print(123)"',
            'sandbox --sandbox-id <sandbox_id> run "python app.py"',
            "sandbox stop <sandbox_id>",
        ],
        "success_signal": "start returns sandbox_id and stop returns status terminated.",
    },
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

COMMANDS_SCHEMA: dict[str, dict[str, Any]] = {
    "start": {
        "summary": "Create a Modal sandbox, print its ID, and leave it running.",
        "creates_sandbox": True,
        "arguments": {},
        "options": {
            "global creation options": "Supports --image, --runtime, --workspace, --workspace-volume, --volume, --env, resources, ports, and timeout flags."
        },
        "output": {
            "sandbox_id": "string",
            "status": "started",
            "workspace": "string",
            "sandbox_timeout": "integer",
            "use_command": "string",
            "stop_command": "string",
        },
        "example": "sandbox --image python:3.13-slim start",
    },
    "stop": {
        "summary": "Terminate a running Modal sandbox by ID.",
        "creates_sandbox": False,
        "arguments": {"sandbox_id": "Modal sandbox object ID. Can also be passed with --sandbox-id."},
        "options": {},
        "output": {"sandbox_id": "string", "status": "terminated"},
        "example": "sandbox stop sb-abc123",
    },
    "run": {
        "summary": "Run a shell command inside a Modal sandbox.",
        "creates_sandbox": True,
        "arguments": {"command": "Shell command string to run."},
        "options": {
            "--cwd": "Working directory inside the sandbox.",
            "--use-command-exit-code": "Return the sandbox command exit code as the CLI exit code.",
            "global --max-output-bytes": "Maximum captured bytes for stdout and stderr separately.",
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
            "--cwd": "Working directory inside the sandbox.",
            "--env KEY=VALUE": "Per-command environment variable. Repeatable.",
            "--use-command-exit-code": "Return the sandbox command exit code as the CLI exit code.",
            "global --max-output-bytes": "Maximum captured bytes for stdout and stderr separately.",
        },
        "output": COMMAND_RESULT_SCHEMA,
        "example": "sandbox --runtime python3.13 run-command python -c 'print(123)'",
    },
    "write": {
        "summary": "Write UTF-8 text to a file inside the sandbox workspace.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {
            "--content": "Inline text content to write.",
            "--content-file": "Local UTF-8 text file to read and write.",
            "--stdin": "Read UTF-8 text from standard input.",
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
        "options": {},
        "output": {"port": "integer", "url": "string"},
        "example": "sandbox --sandbox-id sb-abc123 domain 3000",
    },
    "snapshot": {
        "summary": "Create a volume-backed workspace snapshot checkpoint.",
        "creates_sandbox": True,
        "arguments": {},
        "options": {"requires --workspace-volume": "Snapshot checkpoints are backed by the workspace Modal volume."},
        "output": {"name": "string", "kind": "modal_volume", "workspace": "string", "status": "created"},
        "example": "sandbox --workspace-volume work snapshot",
    },
    "schema": {
        "summary": "Print this machine-readable CLI schema.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {},
        "output": {"schema_version": "string", "commands": "object"},
        "example": "sandbox schema",
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
            "global creation options": "With --run, supports --image, --runtime, --workspace, --workspace-volume, --volume, --env, resources, ports, and timeout flags.",
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


def _sandbox_from_args(args: argparse.Namespace, *, sandbox_id: str | None | object = _USE_ARG_SANDBOX_ID) -> Sandbox:
    """Create a sandbox from parsed CLI flags."""
    effective_sandbox_id = cast(str | None, args.sandbox_id if sandbox_id is _USE_ARG_SANDBOX_ID else sandbox_id)
    return Sandbox.create(
        app_name=args.app_name,
        workspace=args.workspace,
        image=_resolve_cli_image(args.image),
        runtime=args.runtime,
        volumes=_volumes_from_args(args),
        env=_parse_env(args.env) if args.env else None,
        command_timeout=args.timeout,
        sandbox_timeout=args.sandbox_timeout,
        cpu=args.cpu,
        memory=args.memory,
        gpu=args.gpu,
        region=args.region,
        block_network=args.block_network,
        max_output_bytes=args.max_output_bytes,
        encrypted_ports=tuple(args.encrypted_port),
        unencrypted_ports=tuple(args.unencrypted_port),
        sandbox_id=effective_sandbox_id,
    )


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
    return {
        "sandbox_id": sandbox_id,
        "status": "started",
        "workspace": sandbox.config.workspace,
        "sandbox_timeout": sandbox.config.sandbox_timeout,
        "use_command": f'sandbox --sandbox-id {sandbox_id} run "python --version"',
        "stop_command": f"sandbox stop {sandbox_id}",
    }


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
        return "0.1.0"


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
        "environment": {
            "modal_token_id_set": env_has_id,
            "modal_token_secret_set": env_has_secret,
            "complete": has_complete_env,
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
            "--sandbox-id": "Attach to an existing Modal sandbox instead of creating one.",
            "--max-output-bytes": "Maximum captured bytes for stdout and stderr separately. Defaults to 10485760.",
            "--encrypted-port": "Expose an HTTPS Modal tunnel for the given port. Repeatable.",
            "--unencrypted-port": "Expose a TCP Modal tunnel for the given port. Repeatable.",
        },
        "path_rules": {
            "relative_paths": "Resolved inside the sandbox workspace.",
            "absolute_paths": "Used as absolute paths inside the sandbox.",
            "workspace_escape": "Relative paths using '..' cannot escape the workspace.",
        },
        "lifecycle": {
            "creates_or_attaches_per_command": True,
            "safe_discovery_commands": ["schema", "doctor", "quickstart"],
            "live_modal_commands": [
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
                "snapshot",
            ],
            "long_lived_cli_workflow": "Use start to create a sandbox, --sandbox-id to reuse it, and stop to terminate it.",
            "created_sandboxes_close_behavior": "terminate",
            "attached_sandboxes_close_behavior": "detach",
            "persistent_files": "Use --workspace-volume to preserve files across separate CLI commands.",
            "volume_mounts": "Use --volume NAME:/mount to mount additional Modal volumes at absolute sandbox paths.",
        },
        "auth": {
            "requires_modal_credentials": True,
            "setup_commands": SETUP_COMMANDS,
            "environment_variables": ["MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "MODAL_PROFILE"],
        },
        "image_aliases": IMAGE_ALIASES,
        "recommended_first_commands": RECOMMENDED_FIRST_COMMANDS,
        "golden_workflows": GOLDEN_WORKFLOWS,
        "commands": COMMANDS_SCHEMA,
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
    parser.add_argument("--workspace", default="/workspace")
    parser.add_argument("--image", help="Registry image tag or alias such as py313, py312, py311, or ubuntu24.")
    parser.add_argument(
        "--runtime", choices=["python3.13", "node24", "node22"], help="Runtime alias such as python3.13."
    )
    parser.add_argument("--workspace-volume")
    parser.add_argument("--volume", type=_parse_volume, action="append", default=[], metavar="NAME:/MOUNT")
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--sandbox-timeout", type=int, default=300)
    parser.add_argument("--cpu", type=float)
    parser.add_argument("--memory", type=int)
    parser.add_argument("--gpu")
    parser.add_argument("--region")
    parser.add_argument("--block-network", action="store_true")
    parser.add_argument("--sandbox-id")
    parser.add_argument("--max-output-bytes", type=_positive_int, default=10 * 1024 * 1024)
    parser.add_argument("--encrypted-port", type=_positive_int, action="append", default=[], metavar="PORT")
    parser.add_argument("--unencrypted-port", type=_positive_int, action="append", default=[], metavar="PORT")
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")

    subparsers = parser.add_subparsers(dest="command_name", required=True, parser_class=JsonArgumentParser)

    subparsers.add_parser("start", help="Create a sandbox, print its ID, and leave it running.")

    stop_parser = subparsers.add_parser("stop", help="Terminate a running sandbox by ID.")
    stop_parser.add_argument("target_sandbox_id", nargs="?")

    run_parser = subparsers.add_parser("run", help="Run a command inside the sandbox.")
    run_parser.add_argument("--cwd", help="Working directory inside the sandbox.")
    run_parser.add_argument(
        "--use-command-exit-code",
        action="store_true",
        help="Exit with the sandbox command's exit code instead of 0.",
    )
    run_parser.add_argument("command")

    run_command_parser = subparsers.add_parser("run-command", help="Run an argv-style command inside the sandbox.")
    run_command_parser.add_argument("--cwd", help="Working directory inside the sandbox.")
    run_command_parser.add_argument("--env", action="append", default=[], dest="command_env", metavar="KEY=VALUE")
    run_command_parser.add_argument(
        "--use-command-exit-code",
        action="store_true",
        help="Exit with the sandbox command's exit code instead of 0.",
    )
    run_command_parser.add_argument("cmd")
    run_command_parser.add_argument("args", nargs=argparse.REMAINDER)

    write_parser = subparsers.add_parser("write", help="Write a text file inside the sandbox workspace.")
    write_parser.add_argument("path")
    write_input = write_parser.add_mutually_exclusive_group(required=True)
    write_input.add_argument("--content")
    write_input.add_argument("--content-file")
    write_input.add_argument("--stdin", action="store_true", dest="read_stdin")

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

    subparsers.add_parser("snapshot", help="Create a volume-backed workspace snapshot checkpoint.")

    subparsers.add_parser("schema", help="Print a machine-readable CLI schema.")

    subparsers.add_parser("doctor", help="Inspect local Modal setup without creating a sandbox.")

    quickstart_parser = subparsers.add_parser("quickstart", help="Preview or run the beginner quickstart.")
    quickstart_parser.add_argument(
        "--run",
        action="store_true",
        help="Create a short-lived sandbox and run the quickstart command.",
    )

    return parser


def _write_content_from_args(args: argparse.Namespace) -> str:
    if args.content is not None:
        return args.content
    if args.content_file is not None:
        return Path(args.content_file).read_text(encoding="utf-8")
    if args.read_stdin:
        return sys.stdin.read()
    raise argparse.ArgumentTypeError("write requires --content, --content-file, or --stdin")


def main(argv: list[str] | None = None) -> int:
    """Run the sandbox CLI.

    Args:
        argv: Optional argument list. When omitted, argparse reads `sys.argv`.

    Returns:
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command_name == "schema":
        _print_json(_schema_payload())
        return 0

    if args.command_name == "doctor":
        _print_json(_doctor_payload())
        return 0

    if args.command_name == "quickstart" and not args.run:
        _print_json(_quickstart_payload(creates_modal_resources=False))
        return 0

    sandbox: Sandbox | None = None
    try:
        if args.command_name == "quickstart":
            if args.sandbox_id:
                parser.error("--sandbox-id cannot be used with quickstart --run")
            sandbox = _sandbox_from_args(args)
            result = sandbox.run(QUICKSTART_COMMAND)
            payload = result.to_dict()
            payload["creates_modal_resources"] = True
            payload["quickstart"] = _quickstart_payload(creates_modal_resources=True)
            _print_json(payload)
            return 0

        if args.command_name == "start":
            if args.sandbox_id:
                parser.error("--sandbox-id cannot be used with start")
            sandbox = _sandbox_from_args(args, sandbox_id=None)
            payload = _start_payload(sandbox)
            sandbox.detach()
            sandbox = None
            _print_json(payload)
            return 0

        if args.command_name == "stop":
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
            _print_json({"sandbox_id": sandbox_id, "status": "terminated"})
            return 0

        sandbox = _sandbox_from_args(args)
        # Each command creates or attaches to a sandbox, performs one operation,
        # and closes it. Richer lifecycle management can layer on later.
        if args.command_name == "run":
            result = sandbox.run(args.command, cwd=args.cwd, max_output_bytes=args.max_output_bytes)
            _print_json(result.to_dict())
            if args.use_command_exit_code:
                return _command_exit_code(result)
        elif args.command_name == "run-command":
            result = sandbox.run_command(
                args.cmd,
                args.args,
                cwd=args.cwd,
                env=_parse_env(args.command_env) if args.command_env else None,
                max_output_bytes=args.max_output_bytes,
            )
            _print_json(result.to_dict())
            if args.use_command_exit_code:
                return _command_exit_code(result)
        elif args.command_name == "write":
            sandbox.write_text(args.path, _write_content_from_args(args))
            _print_json({"path": args.path, "status": "wrote"})
        elif args.command_name == "read":
            _print_json({"path": args.path, "content": sandbox.read_text(args.path)})
        elif args.command_name == "ls":
            _print_json({"path": args.path, "files": sandbox.list_files(args.path)})
        elif args.command_name == "mkdir":
            parents = not args.no_parents
            sandbox.mkdir(args.path, parents=parents)
            _print_json({"parents": parents, "path": args.path, "status": "created"})
        elif args.command_name == "rm":
            sandbox.remove(args.path, recursive=args.recursive)
            _print_json({"path": args.path, "recursive": args.recursive, "status": "removed"})
        elif args.command_name == "upload":
            sandbox.copy_from_local(args.local_path, args.remote_path)
            _print_json({"local_path": args.local_path, "remote_path": args.remote_path, "status": "uploaded"})
        elif args.command_name == "download":
            sandbox.copy_to_local(args.remote_path, args.local_path)
            _print_json({"local_path": args.local_path, "remote_path": args.remote_path, "status": "downloaded"})
        elif args.command_name == "domain":
            _print_json({"port": args.port, "url": sandbox.domain(args.port)})
        elif args.command_name == "snapshot":
            snapshot = sandbox.create_snapshot()
            _print_json(
                {
                    "kind": snapshot.kind,
                    "name": snapshot.name,
                    "status": "created",
                    "workspace": snapshot.workspace,
                }
            )
        else:
            parser.error(f"Unknown command: {args.command_name}")
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
