"""High-level synchronous SDK facade for Modal Sandboxes."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence

from ._validation import (
    coerce_sandbox_file,
    normalize_cidr_allowlist,
    normalize_domain_allowlist,
    normalize_sandbox_name,
    normalize_tags,
    normalize_volumes,
    resolve_runtime_image,
    validate_network_policy,
    validate_public_http_url,
    validate_volume_mounts,
)
from .commands import CommandResult, SandboxCommand
from .errors import SandboxConfigurationError, SandboxProviderError
from .files import SandboxFile
from .provider_modal import ModalSandboxProvider, SandboxProvider, sandbox_path
from .types import (
    DEFAULT_MAX_OUTPUT_BYTES,
    ImageSpec,
    ReadinessProbeSpec,
    RuntimeSpec,
    SandboxConfig,
    SandboxFileStat,
    SandboxImageSnapshot,
    SandboxSnapshot,
    SandboxWatchEvent,
)
from .volumes import SandboxVolume

DEFAULT_IMAGE_SNAPSHOT_TTL = 30 * 24 * 3600

_TARBALL_SEED_REMOTE_PATH = "/tmp/_sandbox_seed_tarball.py"

TARBALL_SEED_SCRIPT = """\
import os
import pathlib
import sys
import tarfile
import tempfile
import urllib.request

url, destination, strip_text = sys.argv[1], sys.argv[2], sys.argv[3]
strip_components = int(strip_text)
destination_path = pathlib.Path(destination)
destination_path.mkdir(parents=True, exist_ok=True)

with tempfile.NamedTemporaryFile(suffix=".tar") as archive_file:
    with urllib.request.urlopen(url) as response:
        archive_file.write(response.read())
    archive_file.flush()

    with tarfile.open(archive_file.name) as archive:
        safe_members = []
        destination_root = os.path.abspath(destination)
        for member in archive.getmembers():
            parts = pathlib.PurePosixPath(member.name).parts[strip_components:]
            if not parts:
                continue
            member.name = str(pathlib.PurePosixPath(*parts))
            target = os.path.abspath(os.path.join(destination, member.name))
            if target != destination_root and not target.startswith(destination_root + os.sep):
                raise RuntimeError(f"tarball member escapes destination: {member.name}")
            safe_members.append(member)
        archive.extractall(destination, members=safe_members)
"""


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
        readiness_probe: ReadinessProbeSpec = None,
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
            readiness_probe: Optional `SandboxReadinessProbe` or Modal probe
                object used by `wait_until_ready()`.
            sandbox_id: Existing Modal sandbox ID to attach to instead of
                creating a new sandbox.

        Returns:
            A `Sandbox` connected to the created or attached Modal sandbox.
        """
        resolved_image = resolve_runtime_image(runtime, image)
        normalized_name = normalize_sandbox_name(name)
        normalized_tags = normalize_tags(tags)
        normalized_volumes = normalize_volumes(volumes)
        normalized_domain_allowlist = normalize_domain_allowlist(outbound_domain_allowlist)
        normalized_outbound_cidrs = normalize_cidr_allowlist(outbound_cidr_allowlist, "outbound_cidr_allowlist")
        normalized_inbound_cidrs = normalize_cidr_allowlist(inbound_cidr_allowlist, "inbound_cidr_allowlist")
        validate_volume_mounts(normalized_volumes)
        validate_network_policy(
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
            readiness_probe=readiness_probe,
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
        volumes: Sequence[SandboxVolume] | None = None,
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
            volumes: Optional local volume metadata for attach-only helpers
                such as `workspace_checkpoint()` and `sync_workspace()`.
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
            volumes=normalize_volumes(volumes),
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
        volumes: Sequence[SandboxVolume] | None = None,
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
            volumes: Optional local volume metadata for attach-only helpers
                such as `workspace_checkpoint()` and `sync_workspace()`.
            command_timeout: Default timeout in seconds for `run`.
            sandbox_timeout: Stored for config symmetry with `create`.
            workdir: Default working directory for commands.
            max_output_bytes: Maximum captured bytes per output stream.
            ensure_workspace: Whether to create the configured workspace after
                attaching.

        Returns:
            A `Sandbox` connected to the running named Modal sandbox.
        """
        normalized_name = normalize_sandbox_name(name)
        if normalized_name is None:
            raise SandboxConfigurationError("sandbox name must not be empty.")
        config = SandboxConfig(
            app_name=app_name,
            name=normalized_name,
            workspace=workspace,
            volumes=normalize_volumes(volumes),
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
        readiness_probe: ReadinessProbeSpec = None,
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
        from .errors import SandboxNotFoundError, SandboxProviderError

        normalized_name = normalize_sandbox_name(name)
        if normalized_name is None:
            raise SandboxConfigurationError("sandbox name must not be empty.")

        attach_kwargs = dict(
            app_name=app_name,
            workspace=workspace,
            command_timeout=command_timeout,
            sandbox_timeout=sandbox_timeout,
            workdir=workdir,
            max_output_bytes=max_output_bytes,
        )
        create_kwargs = dict(
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
            readiness_probe=readiness_probe,
        )

        # Retry once to handle the race where two callers both see "not found"
        # and then one wins the create; the loser retries from_name.
        for attempt in range(2):
            try:
                return cls.from_name(normalized_name, **attach_kwargs)  # type: ignore[arg-type]
            except SandboxNotFoundError:
                pass
            try:
                sandbox = cls.create(**create_kwargs)  # type: ignore[arg-type]
                if on_create is not None:
                    on_create(sandbox)
                return sandbox
            except SandboxProviderError:
                if attempt == 0:
                    continue
                raise
        raise SandboxNotFoundError(f"Could not find or create sandbox named {normalized_name!r}.")

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
        readiness_probe: ReadinessProbeSpec = None,
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
            readiness_probe=readiness_probe,
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
        chmod_by_mode: dict[int, list[str]] = {}
        for file in files:
            sandbox_file = coerce_sandbox_file(file)
            if isinstance(sandbox_file.content, bytes):
                self.write_bytes(sandbox_file.path, sandbox_file.content)
            else:
                self.write_text(sandbox_file.path, sandbox_file.content)
            if sandbox_file.mode is not None:
                chmod_path = sandbox_path(sandbox_file.path, self.config.workspace)
                chmod_by_mode.setdefault(sandbox_file.mode, []).append(chmod_path)

        for mode, paths in chmod_by_mode.items():
            result = self.run_command("chmod", [f"{mode:o}", *paths])
            if result.exit_code not in (0, None):
                raise SandboxProviderError(f"chmod {mode:o} failed with exit code {result.exit_code}: {result.stderr}")

    def seed_git(
        self,
        repo_url: str,
        *,
        destination: str = ".",
        ref: str | None = None,
        depth: int = 1,
    ) -> CommandResult:
        """Clone a public Git repository into the sandbox.

        Args:
            repo_url: Public HTTP(S) Git repository URL.
            destination: Relative workspace path or absolute sandbox path.
            ref: Optional branch or tag to pass to `git clone --branch`.
            depth: Clone depth. Use `0` for a full clone.

        Returns:
            Command result from the `git clone` invocation.
        """
        repo_url = repo_url.strip()
        validate_public_http_url(repo_url)
        if depth < 0:
            raise SandboxConfigurationError("seed_git depth must be non-negative.")
        target = sandbox_path(destination, self.config.workspace)
        args: list[str] = ["clone"]
        if depth:
            args.extend(["--depth", str(depth)])
        if ref:
            args.extend(["--branch", ref])
        args.extend([repo_url, target])
        return self.run_command("git", args)

    def seed_tarball(
        self,
        tarball_url: str,
        *,
        destination: str = ".",
        strip_components: int = 1,
    ) -> CommandResult:
        """Download and extract a public tarball into the sandbox.

        Args:
            tarball_url: Public HTTP(S) tarball URL.
            destination: Relative workspace path or absolute sandbox path.
            strip_components: Leading path components to remove while
                extracting.

        Returns:
            Command result from the extraction command.
        """
        tarball_url = tarball_url.strip()
        validate_public_http_url(tarball_url)
        if strip_components < 0:
            raise SandboxConfigurationError("strip_components must be non-negative.")
        target = sandbox_path(destination, self.config.workspace)
        self._provider.write_text(_TARBALL_SEED_REMOTE_PATH, TARBALL_SEED_SCRIPT)
        return self.run_command("python", [_TARBALL_SEED_REMOTE_PATH, tarball_url, target, str(strip_components)])

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

    def workspace_checkpoint(self) -> SandboxSnapshot:
        """Create a volume-backed workspace checkpoint.

        Returns:
            Metadata for the Modal volume mounted at the workspace path.

        Raises:
            SandboxConfigurationError: If the workspace is not backed by a
                named volume.
        """
        return self._provider.create_snapshot()

    def create_snapshot(self) -> SandboxSnapshot:
        """Compatibility alias for `workspace_checkpoint()`."""
        return self.workspace_checkpoint()

    def snapshot_filesystem(
        self, *, timeout: int = 55, ttl: int | None = DEFAULT_IMAGE_SNAPSHOT_TTL
    ) -> SandboxImageSnapshot:
        """Snapshot the sandbox filesystem into a Modal image."""
        return self._provider.snapshot_filesystem(timeout=timeout, ttl=ttl)

    def snapshot_directory(
        self,
        path: str,
        *,
        timeout: int = 55,
        ttl: int | None = DEFAULT_IMAGE_SNAPSHOT_TTL,
    ) -> SandboxImageSnapshot:
        """Snapshot a sandbox directory into a Modal image."""
        return self._provider.snapshot_directory(path, timeout=timeout, ttl=ttl)

    def mount_image(self, path: str, image: SandboxImageSnapshot | str | object) -> None:
        """Mount a Modal image snapshot inside the sandbox."""
        self._provider.mount_image(path, image)

    def unmount_image(self, path: str) -> None:
        """Unmount a Modal image snapshot from the sandbox."""
        self._provider.unmount_image(path)

    def stat(self, path: str) -> SandboxFileStat:
        """Return metadata for a sandbox filesystem path."""
        return self._provider.stat(path)

    def watch(
        self,
        path: str,
        *,
        recursive: bool = False,
        timeout: int | None = None,
        filter: Sequence[str] | None = None,
    ) -> Sequence[SandboxWatchEvent]:
        """Return filesystem watch events for a sandbox path."""
        return self._provider.watch(path, recursive=recursive, timeout=timeout, filter=filter)

    def sync_workspace(self) -> CommandResult:
        """Persist workspace-volume changes without waiting for termination."""
        return self._provider.sync_workspace()

    def wait_until_ready(self, *, timeout: int = 300) -> None:
        """Wait until the sandbox readiness probe succeeds.

        Args:
            timeout: Maximum seconds to wait for Modal readiness. Modal raises
                if the sandbox has no readiness probe or the probe does not
                become ready before the timeout.
        """
        self._provider.wait_until_ready(timeout=timeout)

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
