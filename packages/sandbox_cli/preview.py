"""Resource-free CLI execution preview helpers."""

from __future__ import annotations

import argparse

from sandbox import SandboxVolume

from .schema import LIVE_MODAL_COMMANDS


def _volume_payload(volume: SandboxVolume) -> dict[str, object]:
    return {
        "mount_path": volume.mount_path,
        "volume": volume.volume if isinstance(volume.volume, str) else type(volume.volume).__name__,
        "create_if_missing": volume.create_if_missing,
    }


def preview_payload(
    args: argparse.Namespace, *, resolved_image: str | None, volumes: tuple[SandboxVolume, ...]
) -> dict[str, object]:
    """Build a resource-free preview of the resolved live sandbox behavior.

    Args:
        args: Parsed CLI namespace.
        resolved_image: Image alias resolved to a registry tag.
        volumes: Effective volume declarations.

    Returns:
        JSON-serializable preview that does not instantiate `Sandbox`.
    """
    command_name = args.preview_command_name
    attach_target = None
    if args.sandbox_id:
        attach_target = {"kind": "sandbox_id", "value": args.sandbox_id}
    elif args.sandbox_name:
        attach_target = {"kind": "sandbox_name", "value": args.sandbox_name}

    creates_sandbox = attach_target is None and command_name in LIVE_MODAL_COMMANDS
    env_keys = sorted(item.split("=", 1)[0] for item in args.env)
    network = {
        "block_network": args.block_network,
        "outbound_domain_allowlist": list(args.allow_domain),
        "outbound_cidr_allowlist": list(args.allow_cidr),
        "inbound_cidr_allowlist": list(args.allow_inbound_cidr),
    }
    readiness = None
    if args.readiness_tcp is not None:
        readiness = {"kind": "tcp", "port": args.readiness_tcp, "interval_ms": args.readiness_interval_ms}
    elif args.readiness_exec is not None:
        readiness = {
            "kind": "exec",
            "command": list(args.readiness_exec),
            "interval_ms": args.readiness_interval_ms,
        }

    return {
        "status": "preview",
        "creates_modal_resources": False,
        "would_create_or_attach": True,
        "would_create_sandbox": creates_sandbox,
        "would_attach": attach_target is not None,
        "attach_target": attach_target,
        "command": command_name,
        "command_arguments": list(args.preview_args),
        "app_name": args.app_name,
        "name": args.name,
        "workspace": args.workspace,
        "image": resolved_image,
        "runtime": args.runtime,
        "volumes": [_volume_payload(volume) for volume in volumes],
        "env": {"keys": env_keys, "values_redacted": True},
        "network": network,
        "resources": {
            "cpu": args.cpu,
            "memory": args.memory,
            "gpu": args.gpu,
            "region": args.region,
        },
        "ports": {
            "encrypted": list(args.encrypted_port),
            "unencrypted": list(args.unencrypted_port),
        },
        "timeouts": {
            "command_timeout": args.timeout,
            "sandbox_timeout": args.sandbox_timeout,
            "ready_timeout": args.ready_timeout,
        },
        "readiness_probe": readiness,
        "lifecycle": "attach_existing" if attach_target else "create_then_close",
    }
