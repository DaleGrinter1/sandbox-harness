from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .volumes import SandboxVolume

ImageSpec = str | object | None
RuntimeSpec = str | None
DEFAULT_MAX_OUTPUT_BYTES = 10 * 1024 * 1024

__all__ = [
    "DEFAULT_MAX_OUTPUT_BYTES",
    "ImageSpec",
    "RuntimeSpec",
    "SandboxConfig",
    "SandboxSnapshot",
]


@dataclass(frozen=True)
class SandboxSnapshot:
    """Volume-backed snapshot compatibility metadata."""

    name: str
    kind: str
    workspace: str


@dataclass(frozen=True)
class SandboxConfig:
    """Configuration used to create or attach to a sandbox.

    Attributes:
        app_name: Modal app name used for sandbox creation.
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
        max_output_bytes: Maximum captured bytes per output stream.
        encrypted_ports: HTTPS ports exposed through Modal tunnels.
        unencrypted_ports: TCP ports exposed through Modal tunnels.
    """

    app_name: str = "modal-sandbox-sdk"
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
    max_output_bytes: int | None = DEFAULT_MAX_OUTPUT_BYTES
    encrypted_ports: tuple[int, ...] = ()
    unencrypted_ports: tuple[int, ...] = ()
