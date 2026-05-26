from __future__ import annotations

import os
import shlex
import time
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from .types import CommandResult, ImageSpec, SandboxConfig, VolumeSpec


class SandboxProvider(Protocol):
    """Provider protocol used by `Sandbox`.

    A concrete provider can target real Modal sandboxes or a fake test backend.
    The public `Sandbox` class delegates all side effects through this protocol.
    """

    config: SandboxConfig

    def run(self, command: str, timeout: int | None = None, cwd: str | None = None) -> CommandResult:
        ...

    def write_text(self, path: str, content: str) -> None:
        ...

    def write_bytes(self, path: str, content: bytes) -> None:
        ...

    def read_text(self, path: str) -> str:
        ...

    def read_bytes(self, path: str) -> bytes:
        ...

    def list_files(self, path: str = ".") -> list[str]:
        ...

    def mkdir(self, path: str, *, parents: bool = True) -> None:
        ...

    def remove(self, path: str, *, recursive: bool = False) -> None:
        ...

    def copy_from_local(self, local_path: str | os.PathLike[str], remote_path: str) -> None:
        ...

    def copy_to_local(self, remote_path: str, local_path: str | os.PathLike[str]) -> None:
        ...

    def close(self) -> None:
        ...


def _decode_stream(value: object) -> str:
    """Normalize Modal process streams into text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _quote(value: str) -> str:
    return shlex.quote(value)


def sandbox_path(path: str, workspace: str) -> str:
    """Convert relative SDK paths into absolute sandbox paths."""
    if path.startswith("/"):
        return path

    workspace_root = workspace.rstrip("/") or "/"
    parts: list[str] = []
    for part in PurePosixPath(path or ".").parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise ValueError("Relative sandbox paths must not escape the workspace.")
            parts.pop()
            continue
        parts.append(part)

    if not parts:
        return workspace_root
    if workspace_root == "/":
        return f"/{'/'.join(parts)}"
    return f"{workspace_root}/{'/'.join(parts)}"


class ModalSandboxProvider:
    """Provider backed by real Modal Sandbox objects."""

    def __init__(self, sandbox: object, config: SandboxConfig, *, owns_sandbox: bool = True):
        """Initialize the provider.

        Args:
            sandbox: Modal sandbox object.
            config: Effective SDK configuration for this sandbox.
            owns_sandbox: Whether this provider created the sandbox and should
                terminate it on close.
        """
        self._sandbox = sandbox
        self.config = config
        self._owns_sandbox = owns_sandbox

    @classmethod
    def create(cls, config: SandboxConfig | None = None) -> "ModalSandboxProvider":
        """Create a new Modal sandbox from SDK configuration.

        Args:
            config: Optional sandbox configuration. Defaults are used when
                omitted.

        Returns:
            Provider connected to the created Modal sandbox.
        """
        config = config or SandboxConfig()
        modal = cls._load_modal()

        app = modal.App.lookup(config.app_name, create_if_missing=True)
        create_kwargs: dict[str, Any] = {
            "app": app,
            "timeout": config.sandbox_timeout,
            "block_network": config.block_network,
        }

        # Strings keep the public API ergonomic; Modal objects give advanced
        # users full control over custom image construction.
        image = _resolve_image(modal, config.image)
        if image is not None:
            create_kwargs["image"] = image

        # Volumes are deliberately opt-in. The workspace volume is a convenience
        # for the common case, while extra_volumes mirrors Modal's mount map.
        volumes = _resolve_volumes(
            modal,
            workspace=config.workspace,
            workspace_volume=config.workspace_volume,
            extra_volumes=config.extra_volumes,
        )
        if volumes:
            create_kwargs["volumes"] = volumes

        optional_kwargs = {
            "env": dict(config.env) if config.env is not None else None,
            "workdir": config.workdir,
            "cpu": config.cpu,
            "memory": config.memory,
            "gpu": config.gpu,
            "region": config.region,
        }
        create_kwargs.update({key: value for key, value in optional_kwargs.items() if value is not None})

        sandbox = modal.Sandbox.create(**create_kwargs)
        provider = cls(sandbox, config, owns_sandbox=True)
        # Ensure relative file operations have a stable root even without a
        # mounted workspace volume.
        provider.mkdir(config.workspace, parents=True)
        return provider

    @classmethod
    def from_id(
        cls,
        sandbox_id: str,
        config: SandboxConfig | None = None,
    ) -> "ModalSandboxProvider":
        """Attach to an existing Modal sandbox.

        Args:
            sandbox_id: Modal sandbox object ID.
            config: Optional local SDK configuration to use for paths and
                command defaults.

        Returns:
            Provider connected to the existing Modal sandbox.
        """
        config = config or SandboxConfig()
        modal = cls._load_modal()
        provider = cls(modal.Sandbox.from_id(sandbox_id), config, owns_sandbox=False)
        provider.mkdir(config.workspace, parents=True)
        return provider

    @staticmethod
    def _load_modal() -> object:
        """Import Modal lazily so package import stays lightweight."""
        try:
            import modal
        except ImportError as exc:
            raise RuntimeError("Install the 'modal' package to use Modal sandboxes.") from exc
        return modal

    @property
    def filesystem(self) -> object:
        """Return Modal's native sandbox filesystem API."""
        return self._sandbox.filesystem

    def run(self, command: str, timeout: int | None = None, cwd: str | None = None) -> CommandResult:
        """Run a shell command inside the Modal sandbox.

        Args:
            command: Shell command to execute.
            timeout: Optional command timeout in seconds.
            cwd: Optional working directory inside the sandbox.

        Returns:
            Command result with captured output and timing metadata.
        """
        effective_timeout = timeout if timeout is not None else self.config.command_timeout
        effective_cwd = cwd or self.config.workdir or self.config.workspace
        shell_command = f"cd {_quote(effective_cwd)} && {command}"

        start = time.monotonic()
        timed_out = False
        stdout = ""
        stderr = ""
        exit_code: int | None = None
        try:
            # Use a shell wrapper for ergonomic command strings while quoting
            # only the working directory we inject.
            process = self._sandbox.exec("sh", "-lc", shell_command, timeout=effective_timeout)
            stdout = _decode_stream(process.stdout.read())
            stderr = _decode_stream(process.stderr.read())
            process.wait()
            exit_code = getattr(process, "returncode", None)
        except TimeoutError as exc:
            timed_out = True
            stderr = str(exc)
        duration_ms = int((time.monotonic() - start) * 1000)

        return CommandResult(
            command=command,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=duration_ms,
            timed_out=timed_out,
        )

    def write_text(self, path: str, content: str) -> None:
        """Write UTF-8 text through Modal's filesystem API."""
        self.filesystem.write_text(content, sandbox_path(path, self.config.workspace))

    def write_bytes(self, path: str, content: bytes) -> None:
        """Write bytes through Modal's filesystem API."""
        self.filesystem.write_bytes(content, sandbox_path(path, self.config.workspace))

    def read_text(self, path: str) -> str:
        """Read UTF-8 text through Modal's filesystem API."""
        return self.filesystem.read_text(sandbox_path(path, self.config.workspace))

    def read_bytes(self, path: str) -> bytes:
        """Read bytes through Modal's filesystem API."""
        return self.filesystem.read_bytes(sandbox_path(path, self.config.workspace))

    def list_files(self, path: str = ".") -> list[str]:
        """List direct children of a sandbox directory."""
        entries = self.filesystem.list_files(sandbox_path(path, self.config.workspace))
        return sorted(str(getattr(entry, "name", entry)) for entry in entries)

    def mkdir(self, path: str, *, parents: bool = True) -> None:
        """Create a sandbox directory."""
        self.filesystem.make_directory(sandbox_path(path, self.config.workspace), create_parents=parents)

    def remove(self, path: str, *, recursive: bool = False) -> None:
        """Remove a sandbox file or directory."""
        self.filesystem.remove(sandbox_path(path, self.config.workspace), recursive=recursive)

    def copy_from_local(self, local_path: str | os.PathLike[str], remote_path: str) -> None:
        """Copy local data into the sandbox."""
        self.filesystem.copy_from_local(Path(local_path), sandbox_path(remote_path, self.config.workspace))

    def copy_to_local(self, remote_path: str, local_path: str | os.PathLike[str]) -> None:
        """Copy sandbox data to the local filesystem."""
        self.filesystem.copy_to_local(sandbox_path(remote_path, self.config.workspace), Path(local_path))

    def close(self) -> None:
        """Terminate or detach from the Modal sandbox."""
        terminate = getattr(self._sandbox, "terminate", None)
        detach = getattr(self._sandbox, "detach", None)
        if self._owns_sandbox and callable(terminate):
            terminate(wait=True)
        elif callable(detach):
            detach()


def _resolve_image(modal: object, image: ImageSpec) -> object | None:
    """Resolve public image input into a Modal image object."""
    if image is None:
        return None
    if isinstance(image, str):
        return modal.Image.from_registry(image)
    return image


def _resolve_volumes(
    modal: object,
    *,
    workspace: str,
    workspace_volume: VolumeSpec | None,
    extra_volumes: Mapping[str, VolumeSpec] | None,
) -> dict[str, object]:
    """Build Modal's mount-path-to-volume mapping."""
    volumes: dict[str, object] = {}
    if workspace_volume is not None:
        volumes[workspace] = _resolve_volume(modal, workspace_volume)

    for mount_path, volume in (extra_volumes or {}).items():
        volumes[str(mount_path)] = _resolve_volume(modal, volume)
    return volumes


def _resolve_volume(modal: object, volume: VolumeSpec) -> object:
    """Resolve public volume input into a Modal volume object."""
    if isinstance(volume, str):
        return modal.Volume.from_name(volume, create_if_missing=True)
    return volume
