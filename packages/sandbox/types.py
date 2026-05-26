from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


ImageSpec = str | object | None
VolumeSpec = str | object


class ModalAuthenticationError(RuntimeError):
    """Raised when Modal credentials are missing, invalid, or expired."""


@dataclass(frozen=True)
class SandboxConfig:
    """Configuration used to create or attach to a sandbox.

    Attributes:
        app_name: Modal app name used for sandbox creation.
        workspace: Default sandbox directory for relative paths.
        command_timeout: Default timeout in seconds for command execution.
        sandbox_timeout: Modal sandbox lifetime timeout in seconds.
        image: Registry image tag, Modal image object, or `None`.
        workspace_volume: Optional volume mounted at `workspace`.
        extra_volumes: Additional mount-path-to-volume mapping.
        env: Environment variables passed to the sandbox.
        workdir: Default working directory for commands.
        cpu: CPU request passed through to Modal.
        memory: Memory request passed through to Modal.
        gpu: GPU request passed through to Modal.
        region: Region preference passed through to Modal.
        block_network: Whether Modal should block outbound network access.
    """

    app_name: str = "modal-sandbox-sdk"
    workspace: str = "/workspace"
    command_timeout: int = 30
    sandbox_timeout: int = 300
    image: ImageSpec = None
    workspace_volume: VolumeSpec | None = None
    extra_volumes: Mapping[str, VolumeSpec] | None = None
    env: Mapping[str, str | None] | None = None
    workdir: str | None = None
    cpu: float | tuple[float, float] | None = None
    memory: int | tuple[int, int] | None = None
    gpu: str | None = None
    region: str | list[str] | None = None
    block_network: bool = False


@dataclass(frozen=True)
class CommandResult:
    """Result returned after running a command in a sandbox.

    Attributes:
        command: Shell command that was requested.
        stdout: Captured standard output.
        stderr: Captured standard error.
        exit_code: Process exit code, or `None` when unavailable.
        duration_ms: Wall-clock command duration in milliseconds.
        timed_out: Whether command execution hit the configured timeout.
    """

    command: str
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: int
    timed_out: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert the result into a JSON-serializable dictionary.

        Returns:
            Dictionary representation of the command result.
        """
        return asdict(self)
