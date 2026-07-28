"""Command-line interface for Modal Sandbox workflows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, cast

from sandbox import Sandbox

from .auth import credential_status, modal_config_path, modal_setup_commands, verify_modal_token
from .config import apply_config, config_metadata, load_config, provided_options
from .errors import error_type_for_exception
from .parser import (
    build_parser as _build_parser,
)
from .parser import (
    exit_with_error as _exit_with_error,
)
from .parser import (
    parse_env as _parse_env,
)
from .parser import (
    print_json as _print_json,
)
from .parser import (
    readiness_probe_from_args as _readiness_probe_from_args,
)
from .parser import (
    resolve_cli_image as _resolve_cli_image,
)
from .parser import (
    volumes_from_args as _volumes_from_args,
)
from .payloads import (
    PayloadServices,
    agent_manifest_payload,
    doctor_payload,
    dry_command_names,
    dry_payload,
    live_quickstart_command,
    package_version,
    quickstart_payload,
    readiness,
    safe_quickstart_commands,
    schema_payload,
)
from .preview import preview_payload
from .resources import list_modal_apps, sandbox_apps, stop_modal_app
from .schema import QUICKSTART_COMMAND

_USE_ARG_SANDBOX_ID = object()


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
    return package_version()


def _safe_quickstart_commands() -> list[str]:
    """Return recommended commands that do not create Modal resources."""
    return safe_quickstart_commands()


def _live_quickstart_command() -> str:
    """Return the first live Modal verification command."""
    return live_quickstart_command()


def _dry_command_names() -> list[str]:
    """Return dry command names that never create Modal resources."""
    return dry_command_names()


def _schema_payload() -> dict[str, object]:
    """Build the machine-readable CLI contract."""
    return schema_payload(version=_package_version())


def _agent_manifest_payload() -> dict[str, object]:
    """Build a compact low-token manifest for coding agents."""
    return agent_manifest_payload(version=_package_version())


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


def _payload_services() -> PayloadServices:
    """Build dependency hooks for CLI payload helpers."""
    return PayloadServices(
        modal_package_info=_modal_package_info,
        credential_status=_credential_status,
        modal_config_path=_modal_config_path,
        recommended_setup_command=_recommended_setup_command,
        verify_modal_token=verify_modal_token,
    )


def _readiness(modal_package: dict[str, object], credentials: dict[str, object]) -> dict[str, object]:
    """Summarize whether the local environment looks ready for live sandboxes."""
    return readiness(
        modal_package,
        credentials,
        recommended_setup_command=_recommended_setup_command(),
    )


def _dry_payload() -> dict[str, object]:
    """Build safe-discovery command metadata without creating resources."""
    return dry_payload(_payload_services())


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
    """Build local Modal readiness diagnostics without creating resources."""
    return doctor_payload(_payload_services(), verify=verify)


def _quickstart_payload(*, creates_modal_resources: bool) -> dict[str, object]:
    """Build quickstart preview or live-run metadata."""
    return quickstart_payload(_payload_services(), creates_modal_resources=creates_modal_resources)


def build_parser():
    """Build the command-line parser."""
    return _build_parser(package_version=_package_version())


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
