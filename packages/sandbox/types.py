"""Shared public configuration and metadata types for sandboxes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any, TypeAlias

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from .volumes import SandboxVolume

ImageSpec = str | object | None
RuntimeSpec = str | None
ReadinessProbeSpec: TypeAlias = object | None
DEFAULT_MAX_OUTPUT_BYTES = 10 * 1024 * 1024

__all__ = [
    "DEFAULT_MAX_OUTPUT_BYTES",
    "ImageSpec",
    "ReadinessProbeSpec",
    "RuntimeSpec",
    "SandboxConfig",
    "SandboxFileStat",
    "SandboxImageSnapshot",
    "SandboxReadinessProbe",
    "SandboxSnapshot",
    "SandboxWatchEvent",
]


@dataclass(frozen=True)
class SandboxSnapshot:
    """Volume-backed snapshot compatibility metadata.

    Attributes:
        name: Modal volume name backing the workspace checkpoint.
        kind: Snapshot implementation kind. Currently `modal_volume`.
        workspace: Sandbox workspace path mounted to the volume.
    """

    name: str
    kind: str
    workspace: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the checkpoint metadata into a JSON-serializable dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class SandboxImageSnapshot:
    """Modal image-backed sandbox snapshot metadata.

    Attributes:
        image_id: Modal image object ID returned by a filesystem or directory
            snapshot.
        kind: Snapshot implementation kind, such as `modal_filesystem` or
            `modal_directory`.
        path: Sandbox path snapshotted for directory snapshots, or `None` for
            full filesystem snapshots.
        ttl_seconds: Snapshot retention in seconds, or `None` for no expiry.
    """

    image_id: str
    kind: str
    path: str | None = None
    ttl_seconds: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the snapshot metadata into a JSON-serializable dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class SandboxFileStat:
    """JSON-friendly metadata for a sandbox filesystem path."""

    path: str
    kind: str
    size: int | None = None
    permissions: str | None = None
    modified_time: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert file metadata into a JSON-serializable dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class SandboxWatchEvent:
    """JSON-friendly filesystem watch event."""

    path: str
    event_type: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the watch event into a JSON-serializable dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class SandboxReadinessProbe:
    """JSON-friendly Modal sandbox readiness probe specification."""

    kind: str
    port: int | None = None
    command: tuple[str, ...] = ()
    interval_ms: int = 100

    @classmethod
    def tcp(cls, port: int, *, interval_ms: int = 100) -> SandboxReadinessProbe:
        """Create a TCP readiness probe specification."""
        if not isinstance(port, int) or isinstance(port, bool) or port <= 0 or port > 65535:
            raise ValueError("readiness TCP port must be an integer between 1 and 65535.")
        _validate_readiness_interval(interval_ms)
        return cls(kind="tcp", port=port, interval_ms=interval_ms)

    @classmethod
    def exec(cls, command: tuple[str, ...] | list[str], *, interval_ms: int = 100) -> SandboxReadinessProbe:
        """Create an argv-style exec readiness probe specification."""
        _validate_readiness_interval(interval_ms)
        normalized = tuple(str(part) for part in command)
        if not normalized:
            raise ValueError("readiness exec command must not be empty.")
        if any(not part for part in normalized):
            raise ValueError("readiness exec command parts must not be empty.")
        return cls(kind="exec", command=normalized, interval_ms=interval_ms)

    def to_dict(self) -> dict[str, Any]:
        """Convert the readiness probe into a JSON-serializable dictionary."""
        return asdict(self)


@dataclass(frozen=True, config=ConfigDict(arbitrary_types_allowed=True))
class SandboxConfig:
    """Configuration used to create or attach to a sandbox.

    Attributes:
        app_name: Modal app name used for sandbox creation.
        name: Optional Modal sandbox name, unique within the app while running.
        tags: Optional Modal sandbox tags.
        workspace: Default sandbox directory for relative paths.
        command_timeout: Default timeout in seconds for command execution.
        sandbox_timeout: Modal sandbox lifetime timeout in seconds.
        image: Registry image tag, Modal image object, or `None`.
        runtime: Vercel-style runtime alias resolved to a Modal image.
        volumes: First-class volume mounts requested for the sandbox.
        env: Environment variables passed to the sandbox.
        workdir: Default working directory for commands.
        cpu: CPU request passed through to Modal.
        memory: Memory request passed through to Modal.
        gpu: GPU request passed through to Modal.
        region: Region preference passed through to Modal.
        block_network: Whether Modal should block outbound network access.
        outbound_domain_allowlist: Domains that sandbox processes may connect to.
        outbound_cidr_allowlist: CIDR ranges that sandbox processes may connect to.
        inbound_cidr_allowlist: CIDR ranges allowed to connect to tunnels and
            connect tokens.
        max_output_bytes: Maximum captured bytes per output stream.
        encrypted_ports: HTTPS ports exposed through Modal tunnels.
        unencrypted_ports: TCP ports exposed through Modal tunnels.
        readiness_probe: Optional readiness probe spec passed to Modal when
            creating a sandbox.
    """

    app_name: str = "modal-sandbox-sdk"
    name: str | None = None
    tags: Mapping[str, str] | None = None
    workspace: str = "/workspace"
    command_timeout: int = 30
    sandbox_timeout: int = 300
    image: ImageSpec = None
    runtime: RuntimeSpec = None
    volumes: tuple[SandboxVolume, ...] = ()
    env: Mapping[str, str | None] | None = None
    workdir: str | None = None
    cpu: float | tuple[float, float] | None = None
    memory: int | tuple[int, int] | None = None
    gpu: str | None = None
    region: str | list[str] | None = None
    block_network: bool = False
    outbound_domain_allowlist: tuple[str, ...] = ()
    outbound_cidr_allowlist: tuple[str, ...] = ()
    inbound_cidr_allowlist: tuple[str, ...] = ()
    max_output_bytes: int | None = DEFAULT_MAX_OUTPUT_BYTES
    encrypted_ports: tuple[int, ...] = ()
    unencrypted_ports: tuple[int, ...] = ()
    readiness_probe: ReadinessProbeSpec = None


def _validate_readiness_interval(interval_ms: int) -> None:
    """Validate Modal readiness probe polling interval."""
    if not isinstance(interval_ms, int) or isinstance(interval_ms, bool) or interval_ms <= 0:
        raise ValueError("readiness interval_ms must be a positive integer.")
