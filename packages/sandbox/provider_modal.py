"""Modal-backed provider implementation for sandbox operations."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol, TypeVar

from ._modal_adapters import (
    resolve_image,
    resolve_readiness_probe,
    resolve_volumes,
)
from ._modal_errors import (
    is_modal_not_found_error,
    is_transient_error,
    raise_provider_error,
    translate_modal_auth_error,
)
from ._modal_runtime import sandbox_path, sandbox_workdir
from .commands import CommandResult, SandboxCommand
from .errors import SandboxNotFoundError
from .provider_modal_commands import ModalCommandMixin
from .provider_modal_filesystem import ModalFilesystemMixin
from .provider_modal_lifecycle import ModalLifecycleMixin
from .types import (
    SandboxConfig,
    SandboxFileStat,
    SandboxImageSnapshot,
    SandboxSnapshot,
    SandboxWatchEvent,
)

T = TypeVar("T")

__all__ = ["ModalSandboxProvider", "SandboxProvider", "sandbox_path", "sandbox_workdir"]


class SandboxProvider(Protocol):
    """Provider protocol used by `Sandbox`.

    A concrete provider can target real Modal sandboxes or a fake test backend.
    The public `Sandbox` class delegates all side effects through this protocol.
    """

    config: SandboxConfig

    @property
    def sandbox_id(self) -> str | None:
        """Return the provider's sandbox ID when one is available.

        Returns:
            Modal sandbox object ID, or `None` when unavailable.
        """
        ...

    def run(
        self,
        command: str,
        timeout: int | None = None,
        cwd: str | None = None,
        max_output_bytes: int | None = None,
    ) -> CommandResult:
        """Run a shell command in the sandbox.

        Args:
            command: Shell command string to execute.
            timeout: Optional per-call timeout in seconds.
            cwd: Optional working directory inside the sandbox.
            max_output_bytes: Optional per-call output cap.

        Returns:
            Captured command result.
        """
        ...

    def run_command(
        self,
        cmd: str,
        args: Sequence[str] | None = None,
        *,
        cwd: str | None = None,
        env: Mapping[str, str | None] | None = None,
        timeout: int | None = None,
        max_output_bytes: int | None = None,
    ) -> CommandResult:
        """Run an argv-style command without shell wrapping.

        Args:
            cmd: Executable name or path.
            args: Arguments passed directly to the executable.
            cwd: Optional working directory inside the sandbox.
            env: Optional per-command environment variables.
            timeout: Optional per-call timeout in seconds.
            max_output_bytes: Optional per-call output cap.

        Returns:
            Captured command result.
        """
        ...

    def run_command_detached(
        self,
        cmd: str,
        args: Sequence[str] | None = None,
        *,
        cwd: str | None = None,
        env: Mapping[str, str | None] | None = None,
        timeout: int | None = None,
        pty: bool = False,
    ) -> SandboxCommand:
        """Start an argv-style command and return a detached handle.

        Args:
            cmd: Executable name or path.
            args: Arguments passed directly to the executable.
            cwd: Optional working directory inside the sandbox.
            env: Optional per-command environment variables.
            timeout: Optional command timeout in seconds. When omitted, the
                detached command is not bounded by `command_timeout`.
            pty: Whether to request a pseudo-terminal.

        Returns:
            Detached command wrapper.
        """
        ...

    def write_text(self, path: str, content: str) -> None:
        """Write UTF-8 text to a sandbox path.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            content: Text content to write.
        """
        ...

    def write_bytes(self, path: str, content: bytes) -> None:
        """Write bytes to a sandbox path.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            content: Binary content to write.
        """
        ...

    def read_text(self, path: str) -> str:
        """Read UTF-8 text from a sandbox path.

        Args:
            path: Relative workspace path, or absolute sandbox path.

        Returns:
            File contents as text.
        """
        ...

    def read_bytes(self, path: str) -> bytes:
        """Read bytes from a sandbox path.

        Args:
            path: Relative workspace path, or absolute sandbox path.

        Returns:
            File contents as bytes.
        """
        ...

    def list_files(self, path: str = ".") -> list[str]:
        """List direct children of a sandbox directory.

        Args:
            path: Relative workspace path, or absolute sandbox path.

        Returns:
            Sorted file and directory names.
        """
        ...

    def mkdir(self, path: str, *, parents: bool = True) -> None:
        """Create a directory inside the sandbox.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            parents: Whether to create missing parent directories.
        """
        ...

    def remove(self, path: str, *, recursive: bool = False) -> None:
        """Remove a file or directory inside the sandbox.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            recursive: Whether to remove directories recursively.
        """
        ...

    def copy_from_local(self, local_path: str | os.PathLike[str], remote_path: str) -> None:
        """Copy a local file or directory into the sandbox.

        Args:
            local_path: Local filesystem path.
            remote_path: Relative workspace path, or absolute sandbox path.
        """
        ...

    def copy_to_local(self, remote_path: str, local_path: str | os.PathLike[str]) -> None:
        """Copy a sandbox file or directory to the local filesystem.

        Args:
            remote_path: Relative workspace path, or absolute sandbox path.
            local_path: Local filesystem destination path.
        """
        ...

    def detach(self) -> None:
        """Detach from the sandbox without terminating it."""
        ...

    def terminate(self, *, wait: bool = True) -> None:
        """Terminate the sandbox.

        Args:
            wait: Whether to wait for provider termination to complete.
        """
        ...

    def domain(self, port: int) -> str:
        """Return the public URL for a declared sandbox port.

        Args:
            port: Port declared when the sandbox was created.

        Returns:
            Public URL for the sandbox tunnel.
        """
        ...

    def create_snapshot(self) -> SandboxSnapshot:
        """Return metadata for a volume-backed workspace snapshot.

        Returns:
            Snapshot metadata for the mounted workspace volume.
        """
        ...

    def snapshot_filesystem(self, *, timeout: int = 55, ttl: int | None = 30 * 24 * 3600) -> SandboxImageSnapshot:
        """Snapshot the sandbox filesystem into a Modal image."""
        ...

    def snapshot_directory(
        self, path: str, *, timeout: int = 55, ttl: int | None = 30 * 24 * 3600
    ) -> SandboxImageSnapshot:
        """Snapshot a sandbox directory into a Modal image."""
        ...

    def mount_image(self, path: str, image: SandboxImageSnapshot | str | object) -> None:
        """Mount a Modal image snapshot inside the sandbox."""
        ...

    def unmount_image(self, path: str) -> None:
        """Unmount a Modal image snapshot from the sandbox."""
        ...

    def stat(self, path: str) -> SandboxFileStat:
        """Return metadata for a sandbox path."""
        ...

    def watch(
        self,
        path: str,
        *,
        recursive: bool = False,
        timeout: int | None = None,
        filter: Sequence[str] | None = None,
    ) -> Sequence[SandboxWatchEvent]:
        """Return filesystem watch events for a sandbox path."""
        ...

    def sync_workspace(self) -> CommandResult:
        """Persist workspace-volume changes without waiting for termination."""
        ...

    def wait_until_ready(self, *, timeout: int = 300) -> None:
        """Wait until Modal reports the sandbox readiness probe has passed."""
        ...

    def close(self) -> None:
        """Close the provider according to ownership semantics."""
        ...


class ModalSandboxProvider(ModalCommandMixin, ModalFilesystemMixin, ModalLifecycleMixin):
    """Provider backed by real Modal Sandbox objects."""

    def __init__(
        self,
        sandbox: Any,
        config: SandboxConfig,
        *,
        owns_sandbox: bool = True,
        sleeper: Callable[[float], None] = time.sleep,
    ):
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
        self._sleeper = sleeper
        self._closed = False

    @classmethod
    def create(cls, config: SandboxConfig | None = None) -> ModalSandboxProvider:
        """Create a new Modal sandbox from SDK configuration.

        Args:
            config: Optional sandbox configuration. Defaults are used when
                omitted.

        Returns:
            Provider connected to the created Modal sandbox.
        """
        config = config or SandboxConfig()
        modal = None
        try:
            modal = cls._load_modal()
            app = modal.App.lookup(config.app_name, create_if_missing=True)
            create_kwargs: dict[str, Any] = {
                "app": app,
                "timeout": config.sandbox_timeout,
                "block_network": config.block_network,
            }

            # Strings keep the public API ergonomic; Modal objects give advanced
            # users full control over custom image construction.
            image = resolve_image(modal, config.image)
            if image is not None:
                create_kwargs["image"] = image

            volumes = resolve_volumes(modal, volumes=config.volumes)
            if volumes:
                create_kwargs["volumes"] = volumes

            readiness_probe = resolve_readiness_probe(modal, config.readiness_probe)
            if readiness_probe is not None:
                create_kwargs["readiness_probe"] = readiness_probe

            optional_kwargs = {
                "name": config.name,
                "tags": dict(config.tags) if config.tags is not None else None,
                "env": dict(config.env) if config.env is not None else None,
                "workdir": config.workdir,
                "cpu": config.cpu,
                "memory": config.memory,
                "gpu": config.gpu,
                "region": config.region,
                "outbound_domain_allowlist": (
                    list(config.outbound_domain_allowlist) if config.outbound_domain_allowlist else None
                ),
                "outbound_cidr_allowlist": (
                    list(config.outbound_cidr_allowlist) if config.outbound_cidr_allowlist else None
                ),
                "inbound_cidr_allowlist": (
                    list(config.inbound_cidr_allowlist) if config.inbound_cidr_allowlist else None
                ),
                "encrypted_ports": list(config.encrypted_ports) if config.encrypted_ports else None,
                "unencrypted_ports": list(config.unencrypted_ports) if config.unencrypted_ports else None,
            }
            create_kwargs.update({key: value for key, value in optional_kwargs.items() if value is not None})

            sandbox = modal.Sandbox.create(**create_kwargs)
            provider = cls(sandbox, config, owns_sandbox=True)
            # Ensure relative file operations have a stable root even without a
            # mounted workspace volume.
            provider.mkdir(config.workspace, parents=True)
        except Exception as exc:
            translate_modal_auth_error(exc, modal, load_modal=cls._load_modal)
            raise_provider_error(exc, context="creating Modal sandbox")
        return provider

    @classmethod
    def from_name(
        cls,
        name: str,
        config: SandboxConfig | None = None,
        *,
        ensure_workspace: bool = True,
    ) -> ModalSandboxProvider:
        """Attach to an existing running Modal sandbox by name.

        Args:
            name: Modal sandbox name to resolve within the configured app.
            config: Optional local SDK configuration to use for paths and
                command defaults.
            ensure_workspace: Whether to create the configured workspace after
                attaching.

        Returns:
            Provider connected to the existing named Modal sandbox.
        """
        config = config or SandboxConfig(name=name)
        modal = None
        try:
            modal = cls._load_modal()
            provider = cls(modal.Sandbox.from_name(config.app_name, name), config, owns_sandbox=False)
            if ensure_workspace:
                provider.mkdir(config.workspace, parents=True)
        except Exception as exc:
            translate_modal_auth_error(exc, modal, load_modal=cls._load_modal)
            if is_modal_not_found_error(exc, modal, load_modal=cls._load_modal):
                raise SandboxNotFoundError(
                    f"No running Modal sandbox named {name!r} was found in app {config.app_name!r}."
                ) from exc
            raise_provider_error(exc, context=f"attaching to Modal sandbox named {name}")
        return provider

    @classmethod
    def from_id(
        cls,
        sandbox_id: str,
        config: SandboxConfig | None = None,
        *,
        ensure_workspace: bool = True,
    ) -> ModalSandboxProvider:
        """Attach to an existing Modal sandbox.

        Args:
            sandbox_id: Modal sandbox object ID.
            config: Optional local SDK configuration to use for paths and
                command defaults.
            ensure_workspace: Whether to create the configured workspace after
                attaching.

        Returns:
            Provider connected to the existing Modal sandbox.
        """
        config = config or SandboxConfig()
        modal = None
        try:
            modal = cls._load_modal()
            provider = cls(modal.Sandbox.from_id(sandbox_id), config, owns_sandbox=False)
            if ensure_workspace:
                provider.mkdir(config.workspace, parents=True)
        except Exception as exc:
            translate_modal_auth_error(exc, modal, load_modal=cls._load_modal)
            raise_provider_error(exc, context=f"attaching to Modal sandbox {sandbox_id}")
        return provider

    @staticmethod
    def _load_modal() -> Any:
        """Import Modal lazily so package import stays lightweight.

        Returns:
            Imported `modal` module.

        Raises:
            RuntimeError: If the Modal package is not installed.
        """
        try:
            import modal
        except ImportError as exc:
            raise RuntimeError("Install the 'modal' package to use Modal sandboxes.") from exc
        return modal

    @property
    def sandbox_id(self) -> str | None:
        """Return the Modal sandbox object ID when available.

        Returns:
            Sandbox object ID, or `None` if Modal has not exposed one.
        """
        value = getattr(self._sandbox, "object_id", None) or getattr(self._sandbox, "sandbox_id", None)
        return str(value) if value is not None else None

    def _modal_call(
        self,
        operation: Callable[[], T],
        *,
        context: str | None = None,
        retry: bool = False,
        max_attempts: int = 3,
    ) -> T:
        """Run a Modal filesystem operation with SDK error translation and retry.

        Retries up to `max_attempts` times only when the caller marks the
        operation as safe to repeat. Auth errors are never retried.

        Args:
            operation: Zero-argument callable that performs the Modal action.
            context: Optional operation description for error messages.
            retry: Whether this operation is safe to retry after a typed
                transient failure.
            max_attempts: Maximum number of attempts before giving up.

        Returns:
            Result returned by `operation`.

        Raises:
            ModalAuthenticationError: If Modal reports an auth failure.
            SandboxProviderError: For other provider failures.
        """
        delay = 0.5
        for attempt in range(max_attempts):
            try:
                return operation()
            except Exception as exc:
                translate_modal_auth_error(exc, load_modal=self._load_modal)
                if retry and attempt < max_attempts - 1 and is_transient_error(exc):
                    self._sleeper(delay * (2**attempt))
                    continue
                raise_provider_error(exc, context=context)
        raise RuntimeError("Modal operation retry loop exited without returning or raising.")
