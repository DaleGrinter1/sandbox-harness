"""Argument parsing helpers for the sandbox CLI."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from ipaddress import ip_address, ip_network
from typing import Any, NoReturn

from sandbox import SandboxReadinessProbe, SandboxVolume

from .errors import error_payload
from .schema import IMAGE_ALIASES, LIVE_MODAL_COMMANDS


def parse_env(values: list[str]) -> dict[str, str]:
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


def positive_int(value: str) -> int:
    """Parse a positive integer argparse value."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def non_negative_int(value: str) -> int:
    """Parse a non-negative integer argparse value."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a non-negative integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be a non-negative integer")
    return parsed


def positive_float(value: str) -> float:
    """Parse a positive floating-point argparse value."""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a positive number") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive number")
    return parsed


def port(value: str) -> int:
    """Parse a TCP/UDP port argparse value."""
    parsed = positive_int(value)
    if parsed > 65535:
        raise argparse.ArgumentTypeError("port must be an integer between 1 and 65535")
    return parsed


def absolute_sandbox_path(value: str) -> str:
    """Parse an absolute sandbox path argparse value."""
    if not value or not value.startswith("/"):
        raise argparse.ArgumentTypeError("value must be an absolute sandbox path")
    return value


def non_empty_value(value: str) -> str:
    """Normalize a non-empty argparse string value."""
    normalized = value.strip()
    if not normalized:
        raise argparse.ArgumentTypeError("value must not be empty")
    return normalized


def public_http_url(value: str) -> str:
    """Parse a public HTTP(S) URL argparse value."""
    normalized = non_empty_value(value)
    from urllib.parse import urlparse

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("URL must be HTTP(S)")
    if parsed.username or parsed.password:
        raise argparse.ArgumentTypeError("URL must not include embedded credentials")
    return normalized


def watch_event(value: str) -> str:
    """Parse a Modal watch event filter name."""
    normalized = non_empty_value(value)
    if not all(character.isalnum() or character in "_-" for character in normalized):
        raise argparse.ArgumentTypeError("watch event names may only contain letters, numbers, dashes, and underscores")
    return normalized


def readiness_exec(value: str) -> tuple[str, ...]:
    """Parse a readiness exec command into argv parts."""
    normalized = non_empty_value(value)
    try:
        parts = tuple(shlex.split(normalized))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"readiness exec command could not be parsed: {exc}") from exc
    if not parts:
        raise argparse.ArgumentTypeError("readiness exec command must not be empty")
    return parts


def sandbox_name(value: str) -> str:
    """Parse a Modal sandbox name argparse value."""
    normalized = non_empty_value(value)
    if len(normalized) > 63:
        raise argparse.ArgumentTypeError("sandbox name must be shorter than 64 characters")
    if not all(character.isalnum() or character in ".-_" for character in normalized):
        raise argparse.ArgumentTypeError(
            "sandbox name may only contain letters, numbers, dashes, periods, and underscores"
        )
    return normalized


def parse_tag(value: str) -> tuple[str, str]:
    """Parse a repeated `--tag KEY=VALUE` flag."""
    if "=" not in value:
        raise argparse.ArgumentTypeError("--tag values must use KEY=VALUE")
    key, tag_value = value.split("=", 1)
    normalized_key = key.strip()
    if not normalized_key:
        raise argparse.ArgumentTypeError("--tag keys must not be empty")
    return normalized_key, tag_value


def domain_allowlist_value(value: str) -> str:
    """Parse one outbound domain allowlist value."""
    normalized = non_empty_value(value)
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


def cidr_allowlist_value(value: str) -> str:
    """Parse one CIDR allowlist value."""
    normalized = non_empty_value(value)
    if "/" not in normalized:
        raise argparse.ArgumentTypeError("value must be a CIDR range")
    try:
        ip_network(normalized, strict=False)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a valid CIDR range") from exc
    return normalized


def parse_volume(value: str) -> SandboxVolume:
    """Parse a `--volume NAME:/absolute/path` flag."""
    if ":" not in value:
        raise argparse.ArgumentTypeError("--volume values must use NAME:/absolute/path")
    name, mount_path = value.split(":", 1)
    if not name:
        raise argparse.ArgumentTypeError("--volume name must not be empty")
    if not mount_path.startswith("/"):
        raise argparse.ArgumentTypeError("--volume mount path must be absolute")
    return SandboxVolume(volume=name, mount_path=mount_path)


def resolve_cli_image(image: str | None) -> str | None:
    """Resolve a CLI image alias into a registry image tag."""
    if image is None:
        return None
    return IMAGE_ALIASES.get(image.lower(), image)


def volumes_from_args(args: argparse.Namespace) -> tuple[SandboxVolume, ...]:
    """Build SDK volume declarations from global CLI flags."""
    volumes = list(args.volume)
    if args.workspace_volume:
        volumes.insert(0, SandboxVolume.workspace(args.workspace_volume, workspace=args.workspace))
    return tuple(volumes)


def readiness_probe_from_args(args: argparse.Namespace) -> SandboxReadinessProbe | None:
    """Build an SDK readiness probe from CLI flags when one is requested."""
    if args.readiness_tcp is not None:
        return SandboxReadinessProbe.tcp(args.readiness_tcp, interval_ms=args.readiness_interval_ms)
    if args.readiness_exec is not None:
        return SandboxReadinessProbe.exec(args.readiness_exec, interval_ms=args.readiness_interval_ms)
    return None


def print_json(payload: Any, *, file: Any = None) -> None:
    """Print a JSON response for shell-friendly CLI output."""
    print(json.dumps(payload, indent=2), file=file or sys.stdout)


def exit_with_error(parser: argparse.ArgumentParser, error_type: str, message: str, exit_code: int) -> NoReturn:
    """Print a JSON error envelope and terminate argparse."""
    print_json(error_payload(error_type, message, exit_code), file=sys.stderr)
    parser.exit(exit_code)


class JsonArgumentParser(argparse.ArgumentParser):
    """Argument parser that keeps failures machine-readable."""

    def error(self, message: str) -> None:
        """Report argument errors as JSON instead of argparse text."""
        exit_with_error(self, "argument_error", message, 2)


def build_parser(*, package_version: str) -> argparse.ArgumentParser:
    """Build the command-line parser."""
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

    parser.add_argument("--app-name", default="modal-sandbox-sdk")
    parser.add_argument("--config", default="sandbox.toml", help="Project sandbox TOML config path.")
    parser.add_argument("--no-config", action="store_true", help="Ignore project sandbox config.")
    parser.add_argument("--name", type=sandbox_name, help="Name for a newly created sandbox.")
    parser.add_argument("--tag", type=parse_tag, action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--workspace", type=absolute_sandbox_path, default="/workspace")
    parser.add_argument("--image", help="Registry image tag or alias such as py313, py312, py311, or ubuntu24.")
    parser.add_argument(
        "--runtime", choices=["python3.13", "node24", "node22"], help="Runtime alias such as python3.13."
    )
    parser.add_argument("--workspace-volume", type=non_empty_value)
    parser.add_argument("--volume", type=parse_volume, action="append", default=[], metavar="NAME:/MOUNT")
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--timeout", type=positive_int, default=30)
    parser.add_argument("--sandbox-timeout", type=positive_int, default=300)
    parser.add_argument("--cpu", type=positive_float)
    parser.add_argument("--memory", type=positive_int)
    parser.add_argument("--gpu")
    parser.add_argument("--region")
    parser.add_argument("--block-network", action="store_true")
    parser.add_argument("--allow-domain", type=domain_allowlist_value, action="append", default=[], metavar="DOMAIN")
    parser.add_argument("--allow-cidr", type=cidr_allowlist_value, action="append", default=[], metavar="CIDR")
    parser.add_argument("--allow-inbound-cidr", type=cidr_allowlist_value, action="append", default=[], metavar="CIDR")
    parser.add_argument("--sandbox-id")
    parser.add_argument("--sandbox-name", type=sandbox_name)
    parser.add_argument("--max-output-bytes", type=non_negative_int, default=10 * 1024 * 1024)
    parser.add_argument("--encrypted-port", type=port, action="append", default=[], metavar="PORT")
    parser.add_argument("--unencrypted-port", type=port, action="append", default=[], metavar="PORT")
    readiness_group = parser.add_mutually_exclusive_group()
    readiness_group.add_argument("--readiness-tcp", type=port, metavar="PORT")
    readiness_group.add_argument("--readiness-exec", type=readiness_exec, metavar="COMMAND")
    parser.add_argument("--readiness-interval-ms", type=positive_int, default=100)
    parser.add_argument("--wait-ready", action="store_true")
    parser.add_argument("--ready-timeout", type=positive_int, default=300)
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--version", action="version", version=f"%(prog)s {package_version}")

    subparsers = parser.add_subparsers(dest="command_name", parser_class=JsonArgumentParser)
    subparsers.add_parser("start", help="Create a sandbox, print its ID, and leave it running.")

    status_parser = subparsers.add_parser("status", help="List Modal apps for this sandbox project.")
    status_parser.add_argument("--all", action="store_true")
    status_parser.add_argument("--modal-environment")
    status_parser.add_argument("--timeout", type=positive_int, default=30, dest="status_timeout")

    cleanup_parser = subparsers.add_parser("cleanup", help="Preview or stop selected Modal sandbox apps.")
    cleanup_parser.add_argument("--app")
    cleanup_parser.add_argument("--all-sandbox-apps", action="store_true")
    cleanup_parser.add_argument("--modal-environment")
    cleanup_parser.add_argument("--timeout", type=positive_int, default=60, dest="status_timeout")
    cleanup_parser.add_argument("--yes", action="store_true")

    stop_parser = subparsers.add_parser("stop", help="Terminate a running sandbox by ID.")
    stop_parser.add_argument("target_sandbox_id", nargs="?")

    run_parser = subparsers.add_parser("run", help="Run a command inside the sandbox.")
    run_parser.add_argument("--cwd")
    run_parser.add_argument("--use-command-exit-code", action="store_true")
    run_parser.add_argument("command")

    run_command_parser = subparsers.add_parser("run-command", help="Run an argv-style command inside the sandbox.")
    run_command_parser.add_argument("--cwd")
    run_command_parser.add_argument("--env", action="append", default=[], dest="command_env", metavar="KEY=VALUE")
    run_command_parser.add_argument("--use-command-exit-code", action="store_true")
    run_command_parser.add_argument("cmd")
    run_command_parser.add_argument("args", nargs=argparse.REMAINDER)

    write_parser = subparsers.add_parser("write", help="Write a file inside the sandbox workspace.")
    write_parser.add_argument("path")
    write_input = write_parser.add_mutually_exclusive_group(required=True)
    write_input.add_argument("--content")
    write_input.add_argument("--content-file")
    write_input.add_argument("--stdin", action="store_true", dest="read_stdin")
    write_input.add_argument("--binary-file", metavar="PATH")
    write_input.add_argument("--binary-stdin", action="store_true", dest="binary_stdin")

    read_parser = subparsers.add_parser("read", help="Read a text file inside the sandbox workspace.")
    read_parser.add_argument("path")
    ls_parser = subparsers.add_parser("ls", help="List files inside the sandbox workspace.")
    ls_parser.add_argument("path", nargs="?", default=".")
    mkdir_parser = subparsers.add_parser("mkdir", help="Create a directory inside the sandbox workspace.")
    mkdir_parser.add_argument("path")
    mkdir_parser.add_argument("--no-parents", action="store_true")
    rm_parser = subparsers.add_parser("rm", help="Remove a file or directory inside the sandbox workspace.")
    rm_parser.add_argument("path")
    rm_parser.add_argument("-r", "--recursive", action="store_true")
    upload_parser = subparsers.add_parser("upload", help="Copy a local file or directory into the sandbox.")
    upload_parser.add_argument("local_path")
    upload_parser.add_argument("remote_path")
    download_parser = subparsers.add_parser("download", help="Copy a sandbox file or directory to the local machine.")
    download_parser.add_argument("remote_path")
    download_parser.add_argument("local_path")
    domain_parser = subparsers.add_parser("domain", help="Print the public URL for a declared sandbox port.")
    domain_parser.add_argument("port", type=positive_int)
    wait_ready_parser = subparsers.add_parser("wait-ready", help="Wait for an existing sandbox readiness probe.")
    wait_ready_parser.add_argument("--timeout", type=positive_int, default=300, dest="wait_ready_timeout")
    subparsers.add_parser("snapshot", help="Create a volume-backed workspace snapshot checkpoint.")

    snapshot_filesystem_parser = subparsers.add_parser("snapshot-filesystem")
    snapshot_filesystem_parser.add_argument("--timeout", type=positive_int, default=55, dest="snapshot_timeout")
    snapshot_filesystem_ttl = snapshot_filesystem_parser.add_mutually_exclusive_group()
    snapshot_filesystem_ttl.add_argument("--ttl", type=non_negative_int, default=30 * 24 * 3600)
    snapshot_filesystem_ttl.add_argument("--no-ttl", action="store_true")
    snapshot_directory_parser = subparsers.add_parser("snapshot-directory")
    snapshot_directory_parser.add_argument("path")
    snapshot_directory_parser.add_argument("--timeout", type=positive_int, default=55, dest="snapshot_timeout")
    snapshot_directory_ttl = snapshot_directory_parser.add_mutually_exclusive_group()
    snapshot_directory_ttl.add_argument("--ttl", type=non_negative_int, default=30 * 24 * 3600)
    snapshot_directory_ttl.add_argument("--no-ttl", action="store_true")

    mount_image_parser = subparsers.add_parser("mount-image")
    mount_image_parser.add_argument("path")
    mount_image_parser.add_argument("image_id")
    unmount_image_parser = subparsers.add_parser("unmount-image")
    unmount_image_parser.add_argument("path")
    stat_parser = subparsers.add_parser("stat")
    stat_parser.add_argument("path")
    watch_parser = subparsers.add_parser("watch")
    watch_parser.add_argument("path")
    watch_parser.add_argument("--timeout", type=positive_int, required=True, dest="watch_timeout")
    watch_parser.add_argument("--recursive", action="store_true")
    watch_parser.add_argument("--event", type=watch_event, action="append", default=[], dest="watch_events")
    subparsers.add_parser("sync")

    seed_git_parser = subparsers.add_parser("seed-git")
    seed_git_parser.add_argument("url", type=public_http_url)
    seed_git_parser.add_argument("--dest", default=".")
    seed_git_parser.add_argument("--ref")
    seed_git_parser.add_argument("--depth", type=non_negative_int, default=1)
    seed_tarball_parser = subparsers.add_parser("seed-tarball")
    seed_tarball_parser.add_argument("url", type=public_http_url)
    seed_tarball_parser.add_argument("--dest", default=".")
    seed_tarball_parser.add_argument("--strip-components", type=non_negative_int, default=1)

    auth_parser = subparsers.add_parser("auth")
    auth_parser.add_argument("--token-id", dest="token_id", help=argparse.SUPPRESS)
    auth_parser.add_argument("--token-secret", dest="token_secret", help=argparse.SUPPRESS)
    auth_parser.add_argument("--profile", default="default", help=argparse.SUPPRESS)
    auth_parser.add_argument("--force", action="store_true", help=argparse.SUPPRESS)
    preview_parser = subparsers.add_parser("preview")
    preview_parser.add_argument("preview_command_name", choices=LIVE_MODAL_COMMANDS)
    preview_parser.add_argument("preview_args", nargs=argparse.REMAINDER)
    subparsers.add_parser("dry")
    schema_parser = subparsers.add_parser("schema")
    schema_parser.add_argument("--agent", action="store_true")
    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--verify", action="store_true")
    quickstart_parser = subparsers.add_parser("quickstart")
    quickstart_parser.add_argument("--run", action="store_true")
    return parser
