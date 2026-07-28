"""Project configuration loading for the sandbox CLI."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

from sandbox import SandboxVolume

CONFIG_FILE_NAME = "sandbox.toml"

_CONFIG_KEYS = {
    "app_name",
    "name",
    "workspace",
    "image",
    "runtime",
    "workspace_volume",
    "volume",
    "env",
    "timeout",
    "sandbox_timeout",
    "cpu",
    "memory",
    "gpu",
    "region",
    "block_network",
    "allow_domain",
    "allow_cidr",
    "allow_inbound_cidr",
    "sandbox_id",
    "sandbox_name",
    "max_output_bytes",
    "encrypted_port",
    "unencrypted_port",
    "readiness_tcp",
    "readiness_exec",
    "readiness_interval_ms",
    "wait_ready",
    "ready_timeout",
}

_KEY_TO_OPTION = {key: f"--{key.replace('_', '-')}" for key in _CONFIG_KEYS}


def provided_options(argv: list[str] | None) -> set[str]:
    """Return long options explicitly present in argv."""
    tokens = sys.argv[1:] if argv is None else argv
    options: set[str] = set()
    for token in tokens:
        if token == "--":
            break
        if token.startswith("--"):
            options.add(token.split("=", 1)[0])
    return options


def load_config(path: Path) -> tuple[dict[str, Any], Path | None]:
    """Load a project config file if it exists.

    Args:
        path: Path passed through `--config`.

    Returns:
        Tuple of normalized config values and the file path that was loaded.
    """
    if not path.exists():
        return {}, None
    with path.open("rb") as f:
        payload = tomllib.load(f)
    unknown = sorted(set(payload) - _CONFIG_KEYS)
    if unknown:
        raise argparse.ArgumentTypeError(f"unsupported sandbox config keys: {', '.join(unknown)}")
    return dict(payload), path


def _strings(value: object, key: str) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        values = cast(list[object], value)
        if all(isinstance(item, str) for item in values):
            return [cast(str, item) for item in values]
    raise argparse.ArgumentTypeError(f"sandbox config {key!r} must be a string or string array")


def _env_values(value: object) -> list[str]:
    if isinstance(value, dict):
        values = cast(dict[object, object], value)
        if all(isinstance(key, str) and isinstance(item, str) for key, item in values.items()):
            env = cast(dict[str, str], values)
            return [f"{key}={item}" for key, item in sorted(env.items())]
        raise argparse.ArgumentTypeError("sandbox config 'env' must map strings to strings")
    return _strings(value, "env")


def _volume_values(value: object) -> list[SandboxVolume]:
    raw_values = _strings(value, "volume")
    volumes: list[SandboxVolume] = []
    for item in raw_values:
        if ":" not in item:
            raise argparse.ArgumentTypeError("sandbox config 'volume' values must use NAME:/absolute/path")
        name, mount_path = item.split(":", 1)
        if not name or not mount_path.startswith("/"):
            raise argparse.ArgumentTypeError("sandbox config 'volume' values must use NAME:/absolute/path")
        volumes.append(SandboxVolume(volume=name, mount_path=mount_path))
    return volumes


def _readiness_exec(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        import shlex

        parts = tuple(shlex.split(value))
        if parts:
            return parts
    if isinstance(value, list):
        values = cast(list[object], value)
        if all(isinstance(item, str) and item for item in values):
            return tuple(cast(str, item) for item in values)
    raise argparse.ArgumentTypeError("sandbox config 'readiness_exec' must be a command string or string array")


def apply_config(args: argparse.Namespace, config: dict[str, Any], explicit_options: set[str]) -> argparse.Namespace:
    """Merge project config into parsed arguments.

    CLI flags win over config values. This function mutates and returns `args`
    because argparse already owns the namespace.
    """
    args.config_loaded = False
    args.config_path_loaded = None
    for key, value in config.items():
        option = _KEY_TO_OPTION[key]
        if option in explicit_options:
            continue
        if key in {"allow_domain", "allow_cidr", "allow_inbound_cidr", "encrypted_port", "unencrypted_port"}:
            setattr(args, key, _strings(value, key))
        elif key == "env":
            setattr(args, key, _env_values(value))
        elif key == "volume":
            setattr(args, key, _volume_values(value))
        elif key == "readiness_exec":
            setattr(args, key, _readiness_exec(value))
        else:
            setattr(args, key, value)
    args.config_loaded = bool(config)
    return args


def config_metadata(args: argparse.Namespace) -> dict[str, object]:
    """Return JSON metadata about project config use."""
    return {
        "loaded": bool(getattr(args, "config_loaded", False)),
        "path": str(getattr(args, "config_path_loaded", "")) or None,
    }
