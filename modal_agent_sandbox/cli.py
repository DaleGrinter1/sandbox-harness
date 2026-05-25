from __future__ import annotations

import argparse
import json
from typing import Any

from .sandbox import Sandbox


def _sandbox_from_args(args: argparse.Namespace) -> Sandbox:
    return Sandbox.create(
        app_name=args.app_name,
        workspace=args.workspace,
        default_timeout=args.timeout,
        volume_name=args.volume_name,
        use_volume=not args.no_volume,
        sandbox_id=args.sandbox_id,
    )


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sandbox-harness")
    parser.add_argument("--app-name", default="modal-agent-sandbox")
    parser.add_argument("--workspace", default="/workspace")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--volume-name", default="modal-agent-sandbox-workspace")
    parser.add_argument("--no-volume", action="store_true")
    parser.add_argument("--sandbox-id")

    subparsers = parser.add_subparsers(dest="command_name", required=True)

    run_parser = subparsers.add_parser("run", help="Run a command inside the sandbox.")
    run_parser.add_argument("command")

    write_parser = subparsers.add_parser("write", help="Write a file inside the sandbox workspace.")
    write_parser.add_argument("path")
    write_parser.add_argument("--content", required=True)

    read_parser = subparsers.add_parser("read", help="Read a file inside the sandbox workspace.")
    read_parser.add_argument("path")

    ls_parser = subparsers.add_parser("ls", help="List files inside the sandbox workspace.")
    ls_parser.add_argument("path", nargs="?", default=".")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    sandbox = _sandbox_from_args(args)
    try:
        if args.command_name == "run":
            _print_json(sandbox.run(args.command).to_dict())
        elif args.command_name == "write":
            _print_json(sandbox.write_file(args.path, args.content).to_dict())
        elif args.command_name == "read":
            _print_json({"path": args.path, "content": sandbox.read_file(args.path)})
        elif args.command_name == "ls":
            _print_json({"path": args.path, "files": sandbox.list_files(args.path)})
        else:
            parser.error(f"Unknown command: {args.command_name}")
    finally:
        sandbox.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
