from __future__ import annotations

import os
from collections.abc import Mapping

from .provider_modal import ModalSandboxProvider, SandboxProvider
from .types import CommandResult, ImageSpec, SandboxConfig, VolumeSpec


class Sandbox:
    """High-level synchronous wrapper around a Modal Sandbox.

    The class keeps Modal-specific setup behind a small SDK surface while
    exposing common command and filesystem operations inside the sandbox
    workspace.
    """

    def __init__(self, provider: SandboxProvider):
        """Initialize a sandbox from a provider implementation.

        Args:
            provider: Backend provider used to execute commands and filesystem
                operations. Tests can pass a fake provider here.
        """
        self._provider = provider

    @classmethod
    def create(
        cls,
        *,
        app_name: str = "modal-sandbox-sdk",
        workspace: str = "/workspace",
        image: ImageSpec = None,
        workspace_volume: VolumeSpec | None = None,
        extra_volumes: Mapping[str, VolumeSpec] | None = None,
        env: Mapping[str, str | None] | None = None,
        workdir: str | None = None,
        command_timeout: int = 30,
        sandbox_timeout: int = 300,
        timeout: int | None = None,
        cpu: float | tuple[float, float] | None = None,
        memory: int | tuple[int, int] | None = None,
        gpu: str | None = None,
        region: str | list[str] | None = None,
        block_network: bool = False,
        sandbox_id: str | None = None,
    ) -> "Sandbox":
        """Create or attach to a Modal Sandbox.

        Args:
            app_name: Modal app name used for sandbox creation.
            workspace: Default directory for relative file operations and
                commands.
            image: Registry image tag or prebuilt `modal.Image` object.
            workspace_volume: Optional Modal volume name or object mounted at
                `workspace`.
            extra_volumes: Optional mapping of mount paths to Modal volume names
                or objects.
            env: Environment variables passed to the Modal sandbox.
            workdir: Default working directory for commands when `cwd` is not
                provided.
            command_timeout: Default timeout in seconds for `run`.
            sandbox_timeout: Modal sandbox lifetime timeout in seconds.
            timeout: Backward-compatible alias for `command_timeout`.
            cpu: CPU request passed through to Modal.
            memory: Memory request passed through to Modal.
            gpu: GPU request passed through to Modal.
            region: Region preference passed through to Modal.
            block_network: Whether to block outbound network access.
            sandbox_id: Existing Modal sandbox ID to attach to instead of
                creating a new sandbox.

        Returns:
            A `Sandbox` connected to the created or attached Modal sandbox.
        """
        if timeout is not None:
            command_timeout = timeout

        config = SandboxConfig(
            app_name=app_name,
            workspace=workspace,
            command_timeout=command_timeout,
            sandbox_timeout=sandbox_timeout,
            image=image,
            workspace_volume=workspace_volume,
            extra_volumes=extra_volumes,
            env=env,
            workdir=workdir,
            cpu=cpu,
            memory=memory,
            gpu=gpu,
            region=region,
            block_network=block_network,
        )

        # Attach and create share the same public config, but Modal only needs
        # image, volume, and resource options when creating a new sandbox.
        if sandbox_id:
            provider = ModalSandboxProvider.from_id(sandbox_id, config)
        else:
            provider = ModalSandboxProvider.create(config)
        return cls(provider)

    @classmethod
    def from_id(
        cls,
        sandbox_id: str,
        *,
        app_name: str = "modal-sandbox-sdk",
        workspace: str = "/workspace",
        command_timeout: int = 30,
        sandbox_timeout: int = 300,
        workdir: str | None = None,
        ensure_workspace: bool = True,
    ) -> "Sandbox":
        """Attach to an existing Modal Sandbox by ID.

        Args:
            sandbox_id: Modal sandbox object ID.
            app_name: Modal app name associated with the sandbox.
            workspace: Default workspace for relative paths.
            command_timeout: Default timeout in seconds for `run`.
            sandbox_timeout: Stored for config symmetry with `create`.
            workdir: Default working directory for commands.
            ensure_workspace: Whether to create the configured workspace after
                attaching.

        Returns:
            A `Sandbox` connected to the existing Modal sandbox.
        """
        config = SandboxConfig(
            app_name=app_name,
            workspace=workspace,
            command_timeout=command_timeout,
            sandbox_timeout=sandbox_timeout,
            workdir=workdir,
        )
        return cls(ModalSandboxProvider.from_id(sandbox_id, config, ensure_workspace=ensure_workspace))

    @classmethod
    def from_provider(cls, provider: SandboxProvider) -> "Sandbox":
        """Build a `Sandbox` from a provider implementation.

        Args:
            provider: Provider object implementing the sandbox operations.

        Returns:
            A sandbox wrapper using the provided backend.
        """
        return cls(provider)

    @property
    def config(self) -> SandboxConfig:
        """Return the effective sandbox configuration."""
        return self._provider.config

    @property
    def sandbox_id(self) -> str | None:
        """Return the Modal sandbox object ID when available."""
        return self._provider.sandbox_id

    def run(self, command: str, timeout: int | None = None, cwd: str | None = None) -> CommandResult:
        """Run a shell command inside the sandbox.

        Args:
            command: Shell command to execute.
            timeout: Optional command timeout in seconds.
            cwd: Optional working directory inside the sandbox.

        Returns:
            Command output, exit status, duration, and timeout metadata.
        """
        return self._provider.run(command, timeout=timeout, cwd=cwd)

    def write_text(self, path: str, content: str) -> None:
        """Write UTF-8 text inside the sandbox workspace.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            content: Text content to write.
        """
        self._provider.write_text(path, content)

    def write_bytes(self, path: str, content: bytes) -> None:
        """Write bytes inside the sandbox workspace.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            content: Binary content to write.
        """
        self._provider.write_bytes(path, content)

    def read_text(self, path: str) -> str:
        """Read UTF-8 text from inside the sandbox workspace.

        Args:
            path: Relative workspace path, or absolute sandbox path.

        Returns:
            File contents as text.
        """
        return self._provider.read_text(path)

    def read_bytes(self, path: str) -> bytes:
        """Read bytes from inside the sandbox workspace.

        Args:
            path: Relative workspace path, or absolute sandbox path.

        Returns:
            File contents as bytes.
        """
        return self._provider.read_bytes(path)

    def list_files(self, path: str = ".") -> list[str]:
        """List direct children of a sandbox directory.

        Args:
            path: Relative workspace path, or absolute sandbox path.

        Returns:
            Sorted file and directory names.
        """
        return self._provider.list_files(path)

    def mkdir(self, path: str, *, parents: bool = True) -> None:
        """Create a directory inside the sandbox.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            parents: Whether to create missing parent directories.
        """
        self._provider.mkdir(path, parents=parents)

    def remove(self, path: str, *, recursive: bool = False) -> None:
        """Remove a file or directory inside the sandbox.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            recursive: Whether to remove directories recursively.
        """
        self._provider.remove(path, recursive=recursive)

    def copy_from_local(self, local_path: str | os.PathLike[str], remote_path: str) -> None:
        """Copy a local file or directory into the sandbox.

        Args:
            local_path: Local filesystem path.
            remote_path: Relative workspace path, or absolute sandbox path.
        """
        self._provider.copy_from_local(local_path, remote_path)

    def copy_to_local(self, remote_path: str, local_path: str | os.PathLike[str]) -> None:
        """Copy a sandbox file or directory to the local filesystem.

        Args:
            remote_path: Relative workspace path, or absolute sandbox path.
            local_path: Local filesystem destination path.
        """
        self._provider.copy_to_local(remote_path, local_path)

    def write_file(self, path: str, content: str) -> None:
        """Write text to a sandbox file.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            content: Text content to write.
        """
        self.write_text(path, content)

    def read_file(self, path: str) -> str:
        """Read text from a sandbox file.

        Args:
            path: Relative workspace path, or absolute sandbox path.

        Returns:
            File contents as text.
        """
        return self.read_text(path)

    def close(self) -> None:
        """Terminate or detach from the underlying sandbox."""
        self._provider.close()

    def detach(self) -> None:
        """Detach from the underlying sandbox without terminating it."""
        self._provider.detach()

    def terminate(self, *, wait: bool = True) -> None:
        """Terminate the underlying sandbox."""
        self._provider.terminate(wait=wait)

    def __enter__(self) -> "Sandbox":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
