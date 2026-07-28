"""Command-line interface for Modal Sandbox workflows."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any, NoReturn, cast

from sandbox import Sandbox, SandboxReadinessProbe, SandboxVolume

from . import schema as cli_schema
from .auth import credential_status, modal_config_path, modal_setup_commands, verify_modal_token
from .config import CONFIG_FILE_NAME, apply_config, config_metadata, load_config, provided_options
from .errors import error_payload, error_type_for_exception
from .preview import preview_payload
from .resources import list_modal_apps, sandbox_apps, stop_modal_app
from .schema import IMAGE_ALIASES, LIVE_MODAL_COMMANDS, QUICKSTART_COMMAND, RECOMMENDED_FIRST_COMMANDS, SETUP_COMMANDS

_USE_ARG_SANDBOX_ID = object()


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
    """Parse a positive integer argparse value."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def _non_negative_int(value: str) -> int:
    """Parse a non-negative integer argparse value."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a non-negative integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be a non-negative integer")
    return parsed


def _positive_float(value: str) -> float:
    """Parse a positive floating-point argparse value."""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a positive number") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive number")
    return parsed


def _port(value: str) -> int:
    """Parse a TCP/UDP port argparse value."""
    parsed = _positive_int(value)
    if parsed > 65535:
        raise argparse.ArgumentTypeError("port must be an integer between 1 and 65535")
    return parsed


def _absolute_sandbox_path(value: str) -> str:
    """Parse an absolute sandbox path argparse value."""
    if not value or not value.startswith("/"):
        raise argparse.ArgumentTypeError("value must be an absolute sandbox path")
    return value


def _non_empty_value(value: str) -> str:
    """Normalize a non-empty argparse string value."""
    normalized = value.strip()
    if not normalized:
        raise argparse.ArgumentTypeError("value must not be empty")
    return normalized


def _public_http_url(value: str) -> str:
    """Parse a public HTTP(S) URL argparse value."""
    normalized = _non_empty_value(value)
    from urllib.parse import urlparse

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("URL must be HTTP(S)")
    if parsed.username or parsed.password:
        raise argparse.ArgumentTypeError("URL must not include embedded credentials")
    return normalized


def _watch_event(value: str) -> str:
    """Parse a Modal watch event filter name."""
    normalized = _non_empty_value(value)
    if not all(character.isalnum() or character in "_-" for character in normalized):
        raise argparse.ArgumentTypeError("watch event names may only contain letters, numbers, dashes, and underscores")
    return normalized


def _readiness_exec(value: str) -> tuple[str, ...]:
    """Parse a readiness exec command into argv parts."""
    normalized = _non_empty_value(value)
    try:
        parts = tuple(shlex.split(normalized))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"readiness exec command could not be parsed: {exc}") from exc
    if not parts:
        raise argparse.ArgumentTypeError("readiness exec command must not be empty")
    return parts


def _sandbox_name(value: str) -> str:
    """Parse a Modal sandbox name argparse value."""
    normalized = _non_empty_value(value)
    if len(normalized) > 63:
        raise argparse.ArgumentTypeError("sandbox name must be shorter than 64 characters")
    if not all(character.isalnum() or character in ".-_" for character in normalized):
        raise argparse.ArgumentTypeError(
            "sandbox name may only contain letters, numbers, dashes, periods, and underscores"
        )
    return normalized


def _parse_tag(value: str) -> tuple[str, str]:
    """Parse a repeated `--tag KEY=VALUE` flag."""
    if "=" not in value:
        raise argparse.ArgumentTypeError("--tag values must use KEY=VALUE")
    key, tag_value = value.split("=", 1)
    normalized_key = key.strip()
    if not normalized_key:
        raise argparse.ArgumentTypeError("--tag keys must not be empty")
    return normalized_key, tag_value


def _domain_allowlist_value(value: str) -> str:
    """Parse one outbound domain allowlist value."""
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
    """Parse one CIDR allowlist value."""
    normalized = _non_empty_value(value)
    if "/" not in normalized:
        raise argparse.ArgumentTypeError("value must be a CIDR range")
    try:
        ip_network(normalized, strict=False)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a valid CIDR range") from exc
    return normalized


def _parse_volume(value: str) -> SandboxVolume:
    """Parse a `--volume NAME:/absolute/path` flag."""
    if ":" not in value:
        raise argparse.ArgumentTypeError("--volume values must use NAME:/absolute/path")
    name, mount_path = value.split(":", 1)
    if not name:
        raise argparse.ArgumentTypeError("--volume name must not be empty")
    if not mount_path.startswith("/"):
        raise argparse.ArgumentTypeError("--volume mount path must be absolute")
    return SandboxVolume(volume=name, mount_path=mount_path)


def _resolve_cli_image(image: str | None) -> str | None:
    """Resolve a CLI image alias into a registry image tag."""
    if image is None:
        return None
    return IMAGE_ALIASES.get(image.lower(), image)


def _volumes_from_args(args: argparse.Namespace) -> tuple[SandboxVolume, ...]:
    """Build SDK volume declarations from global CLI flags."""
    volumes = list(args.volume)
    if args.workspace_volume:
        volumes.insert(0, SandboxVolume.workspace(args.workspace_volume, workspace=args.workspace))
    return tuple(volumes)


def _readiness_probe_from_args(args: argparse.Namespace) -> SandboxReadinessProbe | None:
    """Build an SDK readiness probe from CLI flags when one is requested."""
    if args.readiness_tcp is not None:
        return SandboxReadinessProbe.tcp(args.readiness_tcp, interval_ms=args.readiness_interval_ms)
    if args.readiness_exec is not None:
        return SandboxReadinessProbe.exec(args.readiness_exec, interval_ms=args.readiness_interval_ms)
    return None


def _sandbox_from_args(args: argparse.Namespace, *, sandbox_id: str | None | object = _USE_ARG_SANDBOX_ID) -> Sandbox:
    """Create or attach to a sandbox from parsed CLI flags.

    Args:
        args: Parsed CLI namespace.
        sandbox_id: Override used by subcommands whose positional sandbox ID
            should take precedence over the global `--sandbox-id` flag.

    Returns:
        SDK sandbox object for the command handler.

    Raises:
        argparse.ArgumentTypeError: If mutually exclusive attach flags are
            combined.
    """
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
    _print_json(error_payload(error_type, message, exit_code), file=sys.stderr)
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
    """Reject invalid lifecycle combinations before creating Modal resources.

    Args:
        args: Parsed CLI namespace.
        parser: Parser used to emit JSON argument errors.

    Raises:
        SystemExit: If an invalid combination is detected.
    """
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
    """Return the installed package version used by CLI metadata."""
    return cli_schema.package_version()


def _safe_quickstart_commands() -> list[str]:
    """Return recommended commands that do not create Modal resources."""
    return cli_schema.safe_quickstart_commands()


def _live_quickstart_command() -> str:
    """Return the first live Modal verification command."""
    return cli_schema.live_quickstart_command()


def _dry_command_names() -> list[str]:
    """Return dry command names that never create Modal resources."""
    return cli_schema.dry_command_names()


def _schema_payload() -> dict[str, object]:
    """Build the machine-readable CLI contract."""
    payload = cli_schema.schema_payload()
    payload["version"] = _package_version()
    return payload


def _agent_manifest_payload() -> dict[str, object]:
    """Build a compact low-token manifest for coding agents."""
    payload = cli_schema.agent_manifest_payload()
    payload["version"] = _package_version()
    return payload


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
    return modal_config_path()


def _credential_status() -> dict[str, object]:
    """Inspect local Modal credential signals without contacting Modal.

    Returns:
        JSON-serializable credential status from environment and config file
        presence.
    """
    return credential_status(_modal_config_path())


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
    elif not credentials["complete"]:
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


def _status_payload(args: argparse.Namespace) -> dict[str, object]:
    """Build read-only Modal app status metadata."""
    result = list_modal_apps(environment=args.modal_environment, timeout=args.status_timeout)
    apps = result.get("apps", [])
    filtered = sandbox_apps(cast(list[dict[str, object]], apps), app_name=args.app_name)
    selected = filtered if args.all else [app for app in filtered if app.get("name") == args.app_name]
    return {
        "status": "ok" if result["ok"] else "error",
        "creates_modal_resources": False,
        "contacts_modal": True,
        "app_name": args.app_name,
        "environment": args.modal_environment,
        "apps": selected,
        "all_sandbox_apps": filtered if args.all else None,
        "summary": {
            "visible_apps": len(selected),
            "sandbox_apps": len(filtered),
            "next_cleanup_command": f"sandbox cleanup --app {args.app_name} --yes" if selected else None,
        },
        "error": result.get("error"),
    }


def _cleanup_payload(args: argparse.Namespace) -> dict[str, object]:
    """Build or execute explicit Modal app cleanup."""
    targets: list[str] = []
    if args.app:
        targets.append(args.app)
    if args.all_sandbox_apps:
        status = list_modal_apps(environment=args.modal_environment, timeout=args.status_timeout)
        if not status.get("ok"):
            return {
                "status": "error",
                "creates_modal_resources": False,
                "contacts_modal": True,
                "stops_modal_resources": False,
                "targets": [],
                "error": status.get("error"),
            }
        targets.extend(
            str(app.get("app_id") or app.get("name"))
            for app in sandbox_apps(cast(list[dict[str, object]], status.get("apps", [])), app_name=args.app_name)
            if app.get("app_id") or app.get("name")
        )
    targets = sorted(set(targets))

    if not targets:
        return {
            "status": "nothing_selected",
            "creates_modal_resources": False,
            "contacts_modal": bool(args.all_sandbox_apps),
            "stops_modal_resources": False,
            "targets": [],
            "next_steps": ["Pass --app APP_ID_OR_NAME --yes, or --all-sandbox-apps --yes."],
        }

    if not args.yes:
        return {
            "status": "dry_run",
            "creates_modal_resources": False,
            "contacts_modal": bool(args.all_sandbox_apps),
            "stops_modal_resources": False,
            "targets": targets,
            "next_steps": ["Rerun with --yes to stop the listed Modal apps."],
        }

    stopped = [
        stop_modal_app(target, environment=args.modal_environment, timeout=args.status_timeout) for target in targets
    ]
    return {
        "status": "stopped" if all(item["ok"] for item in stopped) else "partial_failure",
        "creates_modal_resources": False,
        "contacts_modal": True,
        "stops_modal_resources": True,
        "targets": targets,
        "results": stopped,
    }


def _doctor_payload(*, verify: bool = False) -> dict[str, object]:
    """Build local Modal readiness diagnostics without creating resources.

    Returns:
        JSON-serializable doctor payload.
    """
    modal_package = _modal_package_info()
    credentials = _credential_status()
    verification = None
    if verify:
        verification = verify_modal_token(command=(sys.executable, "-m", "modal", "token", "info"))
        credentials = {**credentials, **verification}
    readiness = _readiness(modal_package, credentials)
    recommended_commands = [*RECOMMENDED_FIRST_COMMANDS]
    if not credentials["complete"]:
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
    elif not credentials["complete"]:
        ready_hint = "Complete Modal credentials were not found. Run modal setup before creating a sandbox."
    elif verify and not credentials["verified"]:
        ready_hint = "Modal credentials are complete locally, but verification failed."
    elif verify:
        ready_hint = "Modal credentials are complete locally and verified by Modal."
    else:
        ready_hint = "Modal credentials are complete locally. Run `sandbox doctor --verify` to verify them with Modal."

    if readiness["ready"]:
        summary = {
            "ready": True,
            "message": ready_hint,
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
        "auth_setup_commands": modal_setup_commands(),
        "verification": verification,
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
    parser.add_argument("--config", default=CONFIG_FILE_NAME, help="Project sandbox TOML config path.")
    parser.add_argument("--no-config", action="store_true", help="Ignore project sandbox config.")
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

    status_parser = subparsers.add_parser("status", help="List Modal apps for this sandbox project.")
    status_parser.add_argument("--all", action="store_true", help="Show all apps that look owned by modal-sandbox.")
    status_parser.add_argument("--modal-environment", help="Modal environment passed to `modal app list`.")
    status_parser.add_argument("--timeout", type=_positive_int, default=30, dest="status_timeout")

    cleanup_parser = subparsers.add_parser("cleanup", help="Preview or stop selected Modal sandbox apps.")
    cleanup_parser.add_argument("--app", help="Modal app ID or name to stop.")
    cleanup_parser.add_argument(
        "--all-sandbox-apps", action="store_true", help="Target every visible modal-sandbox app."
    )
    cleanup_parser.add_argument("--modal-environment", help="Modal environment passed to Modal app commands.")
    cleanup_parser.add_argument("--timeout", type=_positive_int, default=60, dest="status_timeout")
    cleanup_parser.add_argument("--yes", action="store_true", help="Actually stop selected Modal apps.")

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
        "auth", help="Print supported Modal authentication commands without accepting secrets."
    )
    auth_parser.add_argument("--token-id", dest="token_id", help=argparse.SUPPRESS)
    auth_parser.add_argument("--token-secret", dest="token_secret", help=argparse.SUPPRESS)
    auth_parser.add_argument("--profile", default="default", help=argparse.SUPPRESS)
    auth_parser.add_argument("--force", action="store_true", help=argparse.SUPPRESS)

    preview_parser = subparsers.add_parser("preview", help="Preview resolved live behavior without creating resources.")
    preview_parser.add_argument("preview_command_name", choices=LIVE_MODAL_COMMANDS)
    preview_parser.add_argument("preview_args", nargs=argparse.REMAINDER)

    subparsers.add_parser("dry", help="List safe discovery commands that do not create Modal resources.")

    schema_parser = subparsers.add_parser("schema", help="Print a machine-readable CLI schema.")
    schema_parser.add_argument(
        "--agent",
        action="store_true",
        help="Print a compact low-token agent manifest instead of the full CLI schema.",
    )

    doctor_parser = subparsers.add_parser("doctor", help="Inspect local Modal setup without creating a sandbox.")
    doctor_parser.add_argument(
        "--verify",
        action="store_true",
        help="Run `modal token info` to verify credentials without creating sandbox resources.",
    )

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
    explicit_options = provided_options(argv)

    if not args.no_config:
        try:
            config, config_path = load_config(Path(args.config))
            args = apply_config(args, config, explicit_options)
            args.config_path_loaded = config_path
        except argparse.ArgumentTypeError as exc:
            _exit_with_error(parser, "argument_error", str(exc), 2)
    else:
        args.config_loaded = False
        args.config_path_loaded = None

    if args.dry:
        if args.command_name is not None:
            parser.error("--dry cannot be combined with a subcommand; use `sandbox dry`")
        _print_json(_dry_payload())
        return 0
    if args.command_name is None:
        parser.error("a command is required")

    _preflight_args(args, parser)

    if args.command_name == "dry":
        payload = _dry_payload()
        payload["config"] = config_metadata(args)
        _print_json(payload)
        return 0
    if args.command_name == "schema":
        _print_json(_agent_manifest_payload() if args.agent else _schema_payload())
        return 0
    if args.command_name == "doctor":
        _print_json(_doctor_payload(verify=args.verify))
        return 0
    if args.command_name == "status":
        _print_json(_status_payload(args))
        return 0
    if args.command_name == "cleanup":
        _print_json(_cleanup_payload(args))
        return 0
    if args.command_name == "quickstart" and not args.run:
        _print_json(_quickstart_payload(creates_modal_resources=False))
        return 0

    if args.command_name == "auth":
        if args.token_id or args.token_secret:
            _exit_with_error(
                parser,
                "argument_error",
                "`sandbox auth` no longer accepts token secrets as command arguments. Use `uv run modal token set`.",
                2,
            )
        _print_json(
            {
                "status": "manual_setup_required",
                "message": "Use Modal's supported authentication flow; this CLI does not accept secrets.",
                "commands": modal_setup_commands(),
                "config_path": str(_modal_config_path()),
                "creates_modal_resources": False,
            }
        )
        return 0
    if args.command_name == "preview":
        payload = preview_payload(args, resolved_image=_resolve_cli_image(args.image), volumes=_volumes_from_args(args))
        payload["config"] = config_metadata(args)
        _print_json(payload)
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
    except Exception as exc:
        _exit_with_error(parser, error_type_for_exception(exc), str(exc), 1)
    finally:
        if sandbox is not None:
            sandbox.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
