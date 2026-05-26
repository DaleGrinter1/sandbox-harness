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
    run_parser.add_argument("command")

    write_parser = subparsers.add_parser("write", help="Write a text file inside the sandbox workspace.")
    write_parser.add_argument("path")
    write_parser.add_argument("--content", required=True)

    read_parser = subparsers.add_parser("read", help="Read a text file inside the sandbox workspace.")
    read_parser.add_argument("path")

    ls_parser = subparsers.add_parser("ls", help="List files inside the sandbox workspace.")
    ls_parser.add_argument("path", nargs="?", default=".")

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

    sandbox = _sandbox_from_args(args)
    try:
        # Each command creates or attaches to a sandbox, performs one operation,
        # and closes it. Richer lifecycle management can layer on later.
        if args.command_name == "run":
            _print_json(sandbox.run(args.command).to_dict())
        elif args.command_name == "write":
            sandbox.write_text(args.path, args.content)
            _print_json({"path": args.path, "status": "wrote"})
        elif args.command_name == "read":
            _print_json({"path": args.path, "content": sandbox.read_text(args.path)})
        elif args.command_name == "ls":
            _print_json({"path": args.path, "files": sandbox.list_files(args.path)})
        else:
            parser.error(f"Unknown command: {args.command_name}")
    finally:
        sandbox.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
