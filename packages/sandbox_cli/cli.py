from __future__ import annotations

import argparse
import json
from typing import Any

from sandbox import Sandbox


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


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Parser configured with global sandbox creation flags and operational
        subcommands.
    """
    parser = argparse.ArgumentParser(prog="sandbox")

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
