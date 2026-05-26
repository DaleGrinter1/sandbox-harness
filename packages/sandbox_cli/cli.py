from __future__ import annotations

import argparse
import os
import json
from importlib import metadata
from pathlib import Path
from typing import Any

from sandbox import Sandbox
#todo: typa


SETUP_COMMANDS = [
    "modal setup",
    "python -m modal setup",
    "modal token new",
    "modal token set --token-id <token id> --token-secret <token secret>",
]

CLI_SCHEMA_VERSION = "1"

COMMANDS_SCHEMA: dict[str, dict[str, Any]] = {
    "run": {
        "summary": "Run a shell command inside a Modal sandbox.",
        "creates_sandbox": True,
        "arguments": {"command": "Shell command string to run."},
        "options": {
            "--cwd": "Working directory inside the sandbox.",
            "--use-command-exit-code": "Return the sandbox command exit code as the CLI exit code.",
        },
        "output": {
            "command": "string",
            "stdout": "string",
            "stderr": "string",
            "exit_code": "integer|null",
            "duration_ms": "integer",
            "timed_out": "boolean",
        },
        "example": 'sandbox --image python:3.13-slim run "python -c \'print(123)\'"',
    },
    "write": {
        "summary": "Write UTF-8 text to a file inside the sandbox workspace.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {"--content": "Text content to write."},
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
    "schema": {
        "summary": "Print this machine-readable CLI schema.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {},
        "output": {"schema_version": "string", "commands": "object"},
        "example": "sandbox schema",
    },
    "doctor": {
        "summary": "Inspect local Modal package and credential setup without creating a sandbox.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {},
        "output": {
            "modal_package": "object",
            "credentials": "object",
            "setup_commands": "string[]",
            "creates_modal_resources": "false",
        },
        "example": "sandbox doctor",
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


def _sandbox_from_args(args: argparse.Namespace) -> Sandbox:
    """Create a sandbox from parsed CLI flags."""
    return Sandbox.create(
        app_name=args.app_name,
        workspace=args.workspace,
        image=args.image,
        workspace_volume=args.workspace_volume,
        env=_parse_env(args.env) if args.env else None,
        command_timeout=args.timeout,
        sandbox_timeout=args.sandbox_timeout,
        cpu=args.cpu,
        memory=args.memory,
        gpu=args.gpu,
        region=args.region,
        block_network=args.block_network,
        sandbox_id=args.sandbox_id,
    )


def _print_json(payload: Any) -> None:
    """Print a JSON response for shell-friendly CLI output."""
    print(json.dumps(payload, indent=2, sort_keys=True))


def _package_version() -> str:
    try:
        return metadata.version("modal-sandbox-sdk")
    except metadata.PackageNotFoundError:
        return "0.1.0"


def _modal_package_info() -> dict[str, object]:
    try:
        import modal
    except ImportError:
        return {"installed": False, "version": None}

    return {"installed": True, "version": getattr(modal, "__version__", None)}


def _modal_config_path() -> Path:
    return Path.home() / ".modal.toml"


def _credential_status() -> dict[str, object]:
    env_has_id = bool(os.environ.get("MODAL_TOKEN_ID"))
    env_has_secret = bool(os.environ.get("MODAL_TOKEN_SECRET"))
    config_path = _modal_config_path()
    config_exists = config_path.exists()
    has_complete_env = env_has_id and env_has_secret

    if has_complete_env:
        status = "configured_from_environment"
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


def _schema_payload() -> dict[str, object]:
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
            "--image": "Registry image tag passed to Modal.",
            "--workspace-volume": "Modal volume name mounted at the workspace path.",
            "--env KEY=VALUE": "Environment variable passed to the sandbox. Repeatable.",
            "--timeout": "Command timeout in seconds for run.",
            "--sandbox-timeout": "Modal sandbox lifetime timeout in seconds.",
            "--cpu": "CPU request passed through to Modal.",
            "--memory": "Memory request in MiB passed through to Modal.",
            "--gpu": "GPU request passed through to Modal.",
            "--region": "Region preference passed through to Modal.",
            "--block-network": "Block outbound network access from the sandbox.",
            "--sandbox-id": "Attach to an existing Modal sandbox instead of creating one.",
        },
        "path_rules": {
            "relative_paths": "Resolved inside the sandbox workspace.",
            "absolute_paths": "Used as absolute paths inside the sandbox.",
            "workspace_escape": "Relative paths using '..' cannot escape the workspace.",
        },
        "lifecycle": {
            "creates_or_attaches_per_command": True,
            "created_sandboxes_close_behavior": "terminate",
            "attached_sandboxes_close_behavior": "detach",
            "persistent_files": "Use --workspace-volume to preserve files across separate CLI commands.",
        },
        "auth": {
            "requires_modal_credentials": True,
            "setup_commands": SETUP_COMMANDS,
            "environment_variables": ["MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "MODAL_PROFILE"],
        },
        "commands": COMMANDS_SCHEMA,
    }


def _doctor_payload() -> dict[str, object]:
    credentials = _credential_status()
    return {
        "modal_package": _modal_package_info(),
        "credentials": credentials,
        "ready_hint": (
            "Modal credentials appear to be configured."
            if credentials["status"] != "missing_or_unknown"
            else "Modal credentials were not found. Run modal setup before creating a sandbox."
        ),
        "setup_commands": SETUP_COMMANDS,
        "creates_modal_resources": False,
        "next_safe_command": "sandbox schema",
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Parser configured with global sandbox creation flags and operational
        subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="sandbox",
        description=(
            "Run commands and file workflows inside Modal Sandboxes. "
            "Operational commands print JSON. Discovery commands do not create Modal resources."
        ),
        epilog=(
            "Agent-friendly discovery:\n"
            "  sandbox schema   Print command metadata, output shapes, and examples as JSON.\n"
            "  sandbox doctor   Inspect local Modal setup without creating a sandbox.\n\n"
            "First time using Modal? Run `modal setup` to sign in. "
            "For headless environments, set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # These flags intentionally mirror the ergonomic SDK creation options so
    # shell usage and Python usage teach the same mental model.
    parser.add_argument("--app-name", default="modal-sandbox-sdk")
    parser.add_argument("--workspace", default="/workspace")
    parser.add_argument("--image")
    parser.add_argument("--workspace-volume")
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--sandbox-timeout", type=int, default=300)
    parser.add_argument("--cpu", type=float)
    parser.add_argument("--memory", type=int)
    parser.add_argument("--gpu")
    parser.add_argument("--region")
    parser.add_argument("--block-network", action="store_true")
    parser.add_argument("--sandbox-id")
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")

    subparsers = parser.add_subparsers(dest="command_name", required=True)

    run_parser = subparsers.add_parser("run", help="Run a command inside the sandbox.")
    run_parser.add_argument("--cwd", help="Working directory inside the sandbox.")
    run_parser.add_argument(
        "--use-command-exit-code",
        action="store_true",
        help="Exit with the sandbox command's exit code instead of 0.",
    )
    run_parser.add_argument("command")

    write_parser = subparsers.add_parser("write", help="Write a text file inside the sandbox workspace.")
    write_parser.add_argument("path")
    write_parser.add_argument("--content", required=True)

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

    subparsers.add_parser("schema", help="Print a machine-readable CLI schema.")

    subparsers.add_parser("doctor", help="Inspect local Modal setup without creating a sandbox.")

    return parser


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

    sandbox: Sandbox | None = None
    try:
        sandbox = _sandbox_from_args(args)
        # Each command creates or attaches to a sandbox, performs one operation,
        # and closes it. Richer lifecycle management can layer on later.
        if args.command_name == "run":
            result = sandbox.run(args.command, cwd=args.cwd)
            _print_json(result.to_dict())
            if args.use_command_exit_code:
                if result.exit_code is not None:
                    return result.exit_code
                return 124 if result.timed_out else 1
        elif args.command_name == "write":
            sandbox.write_text(args.path, args.content)
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
        else:
            parser.error(f"Unknown command: {args.command_name}")
    except argparse.ArgumentTypeError as exc:
        parser.exit(2, f"sandbox: error: {exc}\n")
    except Exception as exc:
        parser.exit(1, f"sandbox: error: {exc}\n")
    finally:
        if sandbox is not None:
            sandbox.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
