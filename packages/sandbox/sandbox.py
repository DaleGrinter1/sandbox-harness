"""High-level synchronous SDK facade for Modal Sandboxes."""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Mapping, Sequence
from ipaddress import ip_address, ip_network

from .commands import CommandResult, SandboxCommand
from .errors import SandboxConfigurationError, SandboxProviderError
from .files import SandboxFile
from .provider_modal import ModalSandboxProvider, SandboxProvider, sandbox_path
from .types import (
    DEFAULT_MAX_OUTPUT_BYTES,
    ImageSpec,
    RuntimeSpec,
    SandboxConfig,
    SandboxSnapshot,
)
from .volumes import SandboxVolume

RUNTIME_IMAGES = {
    "python3.13": "python:3.13-slim",
    "node24": "node:24-slim",
    "node22": "node:22-slim",
}
SANDBOX_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,63}$")


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
        name: str | None = None,
        tags: Mapping[str, str] | None = None,
        workspace: str = "/workspace",
        image: ImageSpec = None,
        runtime: RuntimeSpec = None,
        volumes: Sequence[SandboxVolume] | None = None,
        env: Mapping[str, str | None] | None = None,
        workdir: str | None = None,
        command_timeout: int = 30,
        sandbox_timeout: int = 300,
        cpu: float | tuple[float, float] | None = None,
        memory: int | tuple[int, int] | None = None,
        gpu: str | None = None,
        region: str | list[str] | None = None,
        block_network: bool = False,
        outbound_domain_allowlist: Sequence[str] | None = None,
        outbound_cidr_allowlist: Sequence[str] | None = None,
        inbound_cidr_allowlist: Sequence[str] | None = None,
        max_output_bytes: int | None = DEFAULT_MAX_OUTPUT_BYTES,
        encrypted_ports: Sequence[int] | None = None,
        unencrypted_ports: Sequence[int] | None = None,
        sandbox_id: str | None = None,
    ) -> Sandbox:
        """Create or attach to a Modal Sandbox.

        Args:
            app_name: Modal app name used for sandbox creation.
            name: Optional Modal sandbox name, unique within the app while it
                is running.
            tags: Optional Modal sandbox tags.
            workspace: Default directory for relative file operations and
                commands.
            image: Registry image tag or prebuilt `modal.Image` object.
            runtime: Vercel-style runtime alias. Supported values are
                `python3.13`, `node24`, and `node22`.
            volumes: First-class volume mounts. Pass `SandboxVolume` objects.
            env: Environment variables passed to the Modal sandbox.
            workdir: Default working directory for commands when `cwd` is not
                provided.
            command_timeout: Default timeout in seconds for `run`.
            sandbox_timeout: Modal sandbox lifetime timeout in seconds.
            cpu: CPU request passed through to Modal.
            memory: Memory request passed through to Modal.
            gpu: GPU request passed through to Modal.
            region: Region preference passed through to Modal.
            block_network: Whether to block outbound network access.
            outbound_domain_allowlist: Domains that sandbox processes may
                connect to. Requests outside the allowlist are blocked by
                Modal infrastructure.
            outbound_cidr_allowlist: CIDR ranges that sandbox processes may
                connect to. Requests outside the allowlist are blocked by
                Modal infrastructure unless also allowed by domain.
            inbound_cidr_allowlist: CIDR ranges allowed to connect to sandbox
                tunnels and connect tokens.
            max_output_bytes: Maximum captured bytes per output stream. Use
                `None` for no SDK truncation.
            encrypted_ports: Ports to expose as HTTPS Modal tunnels.
            unencrypted_ports: Ports to expose as TCP Modal tunnels.
            sandbox_id: Existing Modal sandbox ID to attach to instead of
                creating a new sandbox.

        Returns:
            A `Sandbox` connected to the created or attached Modal sandbox.
        """
        resolved_image = _resolve_runtime_image(runtime, image)
        normalized_name = _normalize_sandbox_name(name)
        normalized_tags = _normalize_tags(tags)
        normalized_volumes = _normalize_volumes(volumes)
        normalized_domain_allowlist = _normalize_domain_allowlist(outbound_domain_allowlist)
        normalized_outbound_cidrs = _normalize_cidr_allowlist(outbound_cidr_allowlist, "outbound_cidr_allowlist")
        normalized_inbound_cidrs = _normalize_cidr_allowlist(inbound_cidr_allowlist, "inbound_cidr_allowlist")
        _validate_volume_mounts(normalized_volumes)
        _validate_network_policy(
            block_network=block_network,
            outbound_domain_allowlist=normalized_domain_allowlist,
            outbound_cidr_allowlist=normalized_outbound_cidrs,
            inbound_cidr_allowlist=normalized_inbound_cidrs,
        )

        config = SandboxConfig(
            app_name=app_name,
            name=normalized_name,
            tags=normalized_tags,
            workspace=workspace,
            command_timeout=command_timeout,
            sandbox_timeout=sandbox_timeout,
            image=resolved_image,
            runtime=runtime,
            volumes=normalized_volumes,
            env=env,
            workdir=workdir,
            cpu=cpu,
            memory=memory,
            gpu=gpu,
            region=region,
            block_network=block_network,
            outbound_domain_allowlist=normalized_domain_allowlist,
            outbound_cidr_allowlist=normalized_outbound_cidrs,
            inbound_cidr_allowlist=normalized_inbound_cidrs,
            max_output_bytes=max_output_bytes,
            encrypted_ports=tuple(encrypted_ports or ()),
            unencrypted_ports=tuple(unencrypted_ports or ()),
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
        max_output_bytes: int | None = DEFAULT_MAX_OUTPUT_BYTES,
        ensure_workspace: bool = True,
    ) -> Sandbox:
        """Attach to an existing Modal Sandbox by ID.

        Args:
            sandbox_id: Modal sandbox object ID.
            app_name: Modal app name associated with the sandbox.
            workspace: Default workspace for relative paths.
            command_timeout: Default timeout in seconds for `run`.
            sandbox_timeout: Stored for config symmetry with `create`.
            workdir: Default working directory for commands.
            max_output_bytes: Maximum captured bytes per output stream.
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
            max_output_bytes=max_output_bytes,
        )
        return cls(ModalSandboxProvider.from_id(sandbox_id, config, ensure_workspace=ensure_workspace))

    @classmethod
    def from_name(
        cls,
        name: str,
        *,
        app_name: str = "modal-sandbox-sdk",
        workspace: str = "/workspace",
        command_timeout: int = 30,
        sandbox_timeout: int = 300,
        workdir: str | None = None,
        max_output_bytes: int | None = DEFAULT_MAX_OUTPUT_BYTES,
        ensure_workspace: bool = True,
    ) -> Sandbox:
        """Attach to a running Modal Sandbox by name.

        Args:
            name: Modal sandbox name to resolve within `app_name`.
            app_name: Modal app name associated with the sandbox.
            workspace: Default workspace for relative paths.
            command_timeout: Default timeout in seconds for `run`.
            sandbox_timeout: Stored for config symmetry with `create`.
            workdir: Default working directory for commands.
            max_output_bytes: Maximum captured bytes per output stream.
            ensure_workspace: Whether to create the configured workspace after
                attaching.

        Returns:
            A `Sandbox` connected to the running named Modal sandbox.
        """
        normalized_name = _normalize_sandbox_name(name)
        if normalized_name is None:
            raise SandboxConfigurationError("sandbox name must not be empty.")
        config = SandboxConfig(
            app_name=app_name,
            name=normalized_name,
            workspace=workspace,
            command_timeout=command_timeout,
            sandbox_timeout=sandbox_timeout,
            workdir=workdir,
            max_output_bytes=max_output_bytes,
        )
        return cls(ModalSandboxProvider.from_name(normalized_name, config, ensure_workspace=ensure_workspace))

    @classmethod
    def get_or_create(
        cls,
        name: str,
        *,
        on_create: Callable[[Sandbox], None] | None = None,
        app_name: str = "modal-sandbox-sdk",
        workspace: str = "/workspace",
        image: ImageSpec = None,
        runtime: RuntimeSpec = None,
        volumes: Sequence[SandboxVolume] | None = None,
        env: Mapping[str, str | None] | None = None,
        workdir: str | None = None,
        command_timeout: int = 30,
        sandbox_timeout: int = 300,
        cpu: float | tuple[float, float] | None = None,
        memory: int | tuple[int, int] | None = None,
        gpu: str | None = None,
        region: str | list[str] | None = None,
        block_network: bool = False,
        outbound_domain_allowlist: Sequence[str] | None = None,
        outbound_cidr_allowlist: Sequence[str] | None = None,
        inbound_cidr_allowlist: Sequence[str] | None = None,
        max_output_bytes: int | None = DEFAULT_MAX_OUTPUT_BYTES,
        encrypted_ports: Sequence[int] | None = None,
        unencrypted_ports: Sequence[int] | None = None,
        tags: Mapping[str, str] | None = None,
    ) -> Sandbox:
        """Attach to a running named sandbox or create it when absent.

        Args:
            name: Modal sandbox name to resolve or create.
            on_create: Optional callback invoked only after a new sandbox is
                created.
            app_name: Modal app name associated with the sandbox.

        Returns:
            Existing or newly created sandbox.
        """
        from .errors import SandboxNotFoundError

        normalized_name = _normalize_sandbox_name(name)
        if normalized_name is None:
            raise SandboxConfigurationError("sandbox name must not be empty.")
        try:
            return cls.from_name(
                normalized_name,
                app_name=app_name,
                workspace=workspace,
                command_timeout=command_timeout,
                sandbox_timeout=sandbox_timeout,
                workdir=workdir,
                max_output_bytes=max_output_bytes,
            )
        except SandboxNotFoundError:
            sandbox = cls.create(
                app_name=app_name,
                name=normalized_name,
                tags=tags,
                workspace=workspace,
                image=image,
                runtime=runtime,
                volumes=volumes,
                env=env,
                workdir=workdir,
                command_timeout=command_timeout,
                sandbox_timeout=sandbox_timeout,
                cpu=cpu,
                memory=memory,
                gpu=gpu,
                region=region,
                block_network=block_network,
                outbound_domain_allowlist=outbound_domain_allowlist,
                outbound_cidr_allowlist=outbound_cidr_allowlist,
                inbound_cidr_allowlist=inbound_cidr_allowlist,
                max_output_bytes=max_output_bytes,
                encrypted_ports=encrypted_ports,
                unencrypted_ports=unencrypted_ports,
            )
            if on_create is not None:
                on_create(sandbox)
            return sandbox

    @classmethod
    def from_snapshot(
        cls,
        name: str,
        *,
        app_name: str = "modal-sandbox-sdk",
        sandbox_name: str | None = None,
        tags: Mapping[str, str] | None = None,
        workspace: str = "/workspace",
        image: ImageSpec = None,
        runtime: RuntimeSpec = None,
        env: Mapping[str, str | None] | None = None,
        workdir: str | None = None,
        command_timeout: int = 30,
        sandbox_timeout: int = 300,
        cpu: float | tuple[float, float] | None = None,
        memory: int | tuple[int, int] | None = None,
        gpu: str | None = None,
        region: str | list[str] | None = None,
        block_network: bool = False,
        outbound_domain_allowlist: Sequence[str] | None = None,
        outbound_cidr_allowlist: Sequence[str] | None = None,
        inbound_cidr_allowlist: Sequence[str] | None = None,
        max_output_bytes: int | None = DEFAULT_MAX_OUTPUT_BYTES,
        encrypted_ports: Sequence[int] | None = None,
        unencrypted_ports: Sequence[int] | None = None,
    ) -> Sandbox:
        """Create a sandbox with a volume-backed workspace snapshot.

        Args:
            name: Modal volume name to mount as the workspace snapshot.
            app_name: Modal app name used for sandbox creation.
            sandbox_name: Optional Modal sandbox name for the restored sandbox.
            workspace: Workspace mount path.
            image: Registry image tag or prebuilt `modal.Image` object.
            runtime: Vercel-style runtime alias.

        Returns:
            A sandbox using `name` as its workspace volume.
        """
        return cls.create(
            app_name=app_name,
            name=sandbox_name,
            tags=tags,
            workspace=workspace,
            image=image,
            runtime=runtime,
            volumes=[SandboxVolume.workspace(name, workspace=workspace)],
            env=env,
            workdir=workdir,
            command_timeout=command_timeout,
            sandbox_timeout=sandbox_timeout,
            cpu=cpu,
            memory=memory,
            gpu=gpu,
            region=region,
            block_network=block_network,
            outbound_domain_allowlist=outbound_domain_allowlist,
            outbound_cidr_allowlist=outbound_cidr_allowlist,
            inbound_cidr_allowlist=inbound_cidr_allowlist,
            max_output_bytes=max_output_bytes,
            encrypted_ports=encrypted_ports,
            unencrypted_ports=unencrypted_ports,
        )

    @classmethod
    def from_provider(cls, provider: SandboxProvider) -> Sandbox:
        """Build a `Sandbox` from a provider implementation.

        Args:
            provider: Provider object implementing the sandbox operations.

        Returns:
            A sandbox wrapper using the provided backend.
        """
        return cls(provider)

    @property
    def config(self) -> SandboxConfig:
        """Return the effective sandbox configuration.

        Returns:
            Sandbox configuration resolved at creation or attachment time.
        """
        return self._provider.config

    @property
    def sandbox_id(self) -> str | None:
        """Return the Modal sandbox object ID when available.

        Returns:
            Modal sandbox object ID, or `None` when unavailable.
        """
        return self._provider.sandbox_id

    def run(
        self,
        command: str,
        timeout: int | None = None,
        cwd: str | None = None,
        max_output_bytes: int | None = None,
    ) -> CommandResult:
        """Run a shell command inside the sandbox.

        Args:
            command: Shell command to execute.
            timeout: Optional command timeout in seconds.
            cwd: Optional working directory inside the sandbox.
            max_output_bytes: Optional per-call maximum captured bytes per
                output stream.

        Returns:
            Command output, exit status, duration, and timeout metadata.
        """
        return self._provider.run(command, timeout=timeout, cwd=cwd, max_output_bytes=max_output_bytes)

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
        """Run an argv-style command inside the sandbox.

        Unlike `run`, this method does not shell-wrap the command string.

        Args:
            cmd: Executable name or path.
            args: Arguments passed directly to the executable.
            cwd: Optional working directory inside the sandbox.
            env: Optional per-command environment variables.
            timeout: Optional per-call timeout in seconds.
            max_output_bytes: Optional per-call output cap.

        Returns:
            Command output, exit status, duration, and timeout metadata.
        """
        return self._provider.run_command(
            cmd,
            args,
            cwd=cwd,
            env=env,
            timeout=timeout,
            max_output_bytes=max_output_bytes,
        )

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
        """Start an argv-style command and return a detached command handle.

        Args:
            cmd: Executable name or path.
            args: Arguments passed directly to the executable.
            cwd: Optional working directory inside the sandbox.
            env: Optional per-command environment variables.
            timeout: Optional command timeout in seconds.
            pty: Whether to request a pseudo-terminal.

        Returns:
            Detached command wrapper.
        """
        return self._provider.run_command_detached(cmd, args, cwd=cwd, env=env, timeout=timeout, pty=pty)

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

    def write_files(self, files: Sequence[SandboxFile | Mapping[str, object]]) -> None:
        """Write multiple text or binary files into the sandbox workspace.

        Args:
            files: Sequence of `SandboxFile` objects or mappings with `path`
                and `content` keys.

        Raises:
            TypeError: If a mapping is missing a string path or string/bytes
                content.
        """
        for file in files:
            sandbox_file = _coerce_sandbox_file(file)
            if isinstance(sandbox_file.content, bytes):
                self.write_bytes(sandbox_file.path, sandbox_file.content)
            else:
                self.write_text(sandbox_file.path, sandbox_file.content)
            if sandbox_file.mode is not None:
                chmod_path = sandbox_path(sandbox_file.path, self.config.workspace)
                result = self.run_command("chmod", [f"{sandbox_file.mode:o}", chmod_path])
                if result.exit_code not in (0, None):
                    raise SandboxProviderError(
                        f"chmod failed for {chmod_path!r} with exit code {result.exit_code}: {result.stderr}"
                    )

    def close(self) -> None:
        """Terminate or detach from the underlying sandbox."""
        self._provider.close()

    def detach(self) -> None:
        """Detach from the underlying sandbox without terminating it."""
        self._provider.detach()

    def terminate(self, *, wait: bool = True) -> None:
        """Terminate the underlying sandbox.

        Args:
            wait: Whether to wait for provider termination to complete.
        """
        self._provider.terminate(wait=wait)

    def domain(self, port: int) -> str:
        """Return the public HTTPS URL for a declared sandbox port.

        Args:
            port: Port declared when the sandbox was created.

        Returns:
            Public URL for the Modal tunnel.
        """
        return self._provider.domain(port)

    def create_snapshot(self) -> SandboxSnapshot:
        """Create a volume-backed workspace snapshot checkpoint.

        Returns:
            Metadata for the Modal volume mounted at the workspace path.

        Raises:
            SandboxConfigurationError: If the workspace is not backed by a
                named volume.
        """
        return self._provider.create_snapshot()

    def __enter__(self) -> Sandbox:
        """Enter a context manager and return this sandbox.

        Returns:
            Current sandbox instance.
        """
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Close the sandbox when leaving a context manager.

        Args:
            exc_type: Exception type raised inside the context, if any.
            exc: Exception raised inside the context, if any.
            tb: Traceback raised inside the context, if any.
        """
        self.close()


def _resolve_runtime_image(runtime: RuntimeSpec, image: ImageSpec) -> ImageSpec:
    """Resolve a runtime alias into a registry image.

    Args:
        runtime: Vercel-style runtime alias.
        image: Explicit registry image or Modal image object.

    Returns:
        Resolved image input for `SandboxConfig`.

    Raises:
        SandboxConfigurationError: If both `runtime` and `image` are provided,
            or if the runtime alias is unsupported.
    """
    if runtime is None:
        return image
    if image is not None:
        raise SandboxConfigurationError("Pass either runtime or image, not both.")
    try:
        return RUNTIME_IMAGES[runtime]
    except KeyError as exc:
        supported = ", ".join(sorted(RUNTIME_IMAGES))
        raise SandboxConfigurationError(f"Unsupported runtime {runtime!r}. Supported runtimes: {supported}.") from exc


def _normalize_sandbox_name(name: str | None) -> str | None:
    """Normalize an optional Modal sandbox name.

    Args:
        name: Optional sandbox name.

    Returns:
        Stripped sandbox name, or `None`.

    Raises:
        TypeError: If the name is not a string.
        SandboxConfigurationError: If the name violates Modal's documented
            syntax.
    """
    if name is None:
        return None
    if not isinstance(name, str):
        raise TypeError("sandbox name must be a string.")
    value = name.strip()
    if not value:
        raise SandboxConfigurationError("sandbox name must not be empty.")
    if not SANDBOX_NAME_RE.fullmatch(value):
        raise SandboxConfigurationError(
            "sandbox name must be shorter than 64 characters and contain only letters, numbers, dashes, periods, and underscores."
        )
    return value


def _normalize_tags(tags: Mapping[str, str] | None) -> dict[str, str] | None:
    """Normalize optional Modal sandbox tags.

    Args:
        tags: Optional tag mapping.

    Returns:
        Plain dictionary of tags, or `None`.

    Raises:
        TypeError: If tag keys or values are not strings.
        SandboxConfigurationError: If a tag key is empty.
    """
    if tags is None:
        return None

    normalized: dict[str, str] = {}
    for key, value in tags.items():
        if not isinstance(key, str):
            raise TypeError("sandbox tag keys must be strings.")
        if not isinstance(value, str):
            raise TypeError("sandbox tag values must be strings.")
        normalized_key = key.strip()
        if not normalized_key:
            raise SandboxConfigurationError("sandbox tag keys must not be empty.")
        normalized[normalized_key] = value
    return normalized


def _coerce_sandbox_file(file: SandboxFile | Mapping[str, object]) -> SandboxFile:
    """Normalize bulk file input into a `SandboxFile`.

    Args:
        file: Existing `SandboxFile`, or mapping with `path` and `content`.

    Returns:
        Normalized `SandboxFile`.

    Raises:
        TypeError: If the mapping shape is invalid.
    """
    if isinstance(file, SandboxFile):
        _validate_file_mode(file.mode)
        return file
    path = file.get("path")
    content = file.get("content")
    mode = _coerce_file_mode(file.get("mode"))
    if not isinstance(path, str):
        raise TypeError("Sandbox file mappings must include a string 'path'.")
    if not isinstance(content, (str, bytes)):
        raise TypeError("Sandbox file mappings must include string or bytes 'content'.")
    return SandboxFile(path=path, content=content, mode=mode)


def _coerce_file_mode(mode: object) -> int | None:
    """Normalize an optional mapping file mode.

    Args:
        mode: Optional mode value from a mapping.

    Returns:
        Integer mode, or `None`.

    Raises:
        TypeError: If the mode is not an integer.
        SandboxConfigurationError: If the mode is outside the POSIX range.
    """
    if mode is None:
        return None
    if not isinstance(mode, int) or isinstance(mode, bool):
        raise TypeError("Sandbox file mode must be an integer.")
    _validate_file_mode(mode)
    return mode


def _validate_file_mode(mode: int | None) -> None:
    """Validate an optional POSIX file mode.

    Args:
        mode: Optional integer mode.

    Raises:
        TypeError: If the mode is not an integer.
        SandboxConfigurationError: If the mode is outside the POSIX range.
    """
    if mode is None:
        return
    if not isinstance(mode, int) or isinstance(mode, bool):
        raise TypeError("Sandbox file mode must be an integer.")
    if mode < 0 or mode > 0o7777:
        raise SandboxConfigurationError("Sandbox file mode must be between 0o0000 and 0o7777.")


def _normalize_volumes(volumes: Sequence[SandboxVolume] | None) -> tuple[SandboxVolume, ...]:
    """Normalize optional volume input into an immutable tuple.

    Args:
        volumes: Optional sequence of `SandboxVolume` declarations.

    Returns:
        Tuple of volume declarations.

    Raises:
        TypeError: If any item is not a `SandboxVolume`.
    """
    if volumes is None:
        return ()
    normalized = tuple(volumes)
    for volume in normalized:
        if not isinstance(volume, SandboxVolume):
            raise TypeError("volumes must contain SandboxVolume instances.")
    return normalized


def _normalize_domain_allowlist(domains: Sequence[str] | None) -> tuple[str, ...]:
    """Normalize optional outbound domain allowlist values.

    Args:
        domains: Optional sequence of domain names.

    Returns:
        Tuple of stripped domain names.

    Raises:
        TypeError: If any item is not a string.
        SandboxConfigurationError: If any item is empty.
    """
    if domains is None:
        return ()
    normalized: list[str] = []
    for domain in domains:
        if not isinstance(domain, str):
            raise TypeError("outbound_domain_allowlist must contain strings.")
        value = domain.strip()
        if not value:
            raise SandboxConfigurationError("outbound_domain_allowlist values must not be empty.")
        normalized.append(_validate_domain_allowlist_value(value))
    return tuple(normalized)


def _validate_domain_allowlist_value(value: str) -> str:
    """Validate one Modal outbound domain allowlist entry.

    Args:
        value: Stripped allowlist entry.

    Returns:
        The validated value.

    Raises:
        SandboxConfigurationError: If the value is not a hostname-style domain.
    """
    if any(character.isspace() for character in value):
        raise SandboxConfigurationError("outbound_domain_allowlist values must not contain whitespace.")
    if any(fragment in value for fragment in ("://", "/", "\\", ":", "@")):
        raise SandboxConfigurationError("outbound_domain_allowlist values must be hostnames, not URLs.")

    wildcard = value.startswith("*.")
    hostname = value[2:] if wildcard else value
    if not hostname or len(hostname) > 253:
        raise SandboxConfigurationError("outbound_domain_allowlist values must be valid hostnames.")
    if hostname.startswith(".") or hostname.endswith(".") or ".." in hostname:
        raise SandboxConfigurationError("outbound_domain_allowlist values must be valid hostnames.")

    try:
        ip_address(hostname)
    except ValueError:
        pass
    else:
        raise SandboxConfigurationError(
            "outbound_domain_allowlist values must be domain names; use outbound_cidr_allowlist for IP ranges."
        )

    for label in hostname.split("."):
        if not label or len(label) > 63:
            raise SandboxConfigurationError("outbound_domain_allowlist values must be valid hostnames.")
        if label.startswith("-") or label.endswith("-"):
            raise SandboxConfigurationError("outbound_domain_allowlist values must be valid hostnames.")
        if not all(character.isalnum() or character == "-" for character in label):
            raise SandboxConfigurationError("outbound_domain_allowlist values must be valid hostnames.")

    return value


def _normalize_cidr_allowlist(cidrs: Sequence[str] | None, field_name: str) -> tuple[str, ...]:
    """Normalize optional CIDR allowlist values.

    Args:
        cidrs: Optional sequence of CIDR strings.
        field_name: Public field name used in error messages.

    Returns:
        Tuple of stripped CIDR strings.

    Raises:
        TypeError: If any item is not a string.
        SandboxConfigurationError: If any item is empty or invalid.
    """
    if cidrs is None:
        return ()

    normalized: list[str] = []
    for cidr in cidrs:
        if not isinstance(cidr, str):
            raise TypeError(f"{field_name} must contain strings.")
        value = cidr.strip()
        if not value:
            raise SandboxConfigurationError(f"{field_name} values must not be empty.")
        if "/" not in value:
            raise SandboxConfigurationError(f"{field_name} values must be CIDR ranges.")
        try:
            ip_network(value, strict=False)
        except ValueError as exc:
            raise SandboxConfigurationError(f"{field_name} values must be valid CIDR ranges.") from exc
        normalized.append(value)
    return tuple(normalized)


def _validate_network_policy(
    *,
    block_network: bool,
    outbound_domain_allowlist: Sequence[str],
    outbound_cidr_allowlist: Sequence[str],
    inbound_cidr_allowlist: Sequence[str],
) -> None:
    """Validate Modal network policy combinations.

    Args:
        block_network: Whether all outbound network access is blocked.
        outbound_domain_allowlist: Domain allowlist entries.
        outbound_cidr_allowlist: Outbound CIDR allowlist entries.
        inbound_cidr_allowlist: Inbound CIDR allowlist entries.

    Raises:
        SandboxConfigurationError: If `block_network` is combined with an
            allowlist that Modal rejects.
    """
    if block_network and (outbound_domain_allowlist or outbound_cidr_allowlist or inbound_cidr_allowlist):
        raise SandboxConfigurationError(
            "block_network cannot be combined with outbound_domain_allowlist, "
            "outbound_cidr_allowlist, or inbound_cidr_allowlist."
        )


def _validate_volume_mounts(volumes: Sequence[SandboxVolume]) -> None:
    """Validate volume mount paths before passing them to Modal.

    Args:
        volumes: Volume declarations to validate.

    Raises:
        SandboxConfigurationError: If a mount path is not absolute or if two
            volumes target the same normalized mount path.
    """
    seen: set[str] = set()

    def add_mount(mount_path: str) -> None:
        """Track one normalized mount path and reject duplicates."""
        normalized = mount_path.rstrip("/") or "/"
        if normalized in seen:
            raise SandboxConfigurationError(f"Duplicate sandbox volume mount path: {normalized}")
        seen.add(normalized)

    for volume in volumes:
        if not volume.mount_path.startswith("/"):
            raise SandboxConfigurationError("Sandbox volume mount_path must be an absolute sandbox path.")
        add_mount(volume.mount_path)
