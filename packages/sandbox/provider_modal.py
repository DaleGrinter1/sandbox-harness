"""Modal-backed provider implementation for sandbox operations."""

from __future__ import annotations

import os
import shlex
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from importlib import import_module
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, Protocol, TypeVar

from .commands import CommandResult, SandboxCommand
from .errors import ModalAuthenticationError, SandboxConfigurationError, SandboxNotFoundError, SandboxProviderError
from .types import (
    ImageSpec,
    SandboxConfig,
    SandboxFileStat,
    SandboxImageSnapshot,
    SandboxReadinessProbe,
    SandboxSnapshot,
    SandboxWatchEvent,
)
from .volumes import SandboxVolume, VolumeSpec

T = TypeVar("T")

_TRANSIENT_ERROR_KEYWORDS = frozenset(
    ["connection", "timeout", "network", "unavailable", "retry", "reset", "refused", "temporary"]
)


def _is_transient_error(exc: Exception) -> bool:
    return any(kw in str(exc).lower() for kw in _TRANSIENT_ERROR_KEYWORDS)


MODAL_AUTH_GUIDANCE = """Modal authentication is required to use Modal sandboxes.

Run one of these commands to sign in:
  modal setup
  python -m modal setup

For non-interactive environments, configure a Modal token instead:
  modal token new

You can also provide credentials with MODAL_TOKEN_ID and MODAL_TOKEN_SECRET.
After setup completes, retry your sandbox command."""


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


def _decode_stream(value: object) -> str:
    """Normalize Modal process streams into text.

    Args:
        value: Raw stream value returned by Modal. It may be bytes, text, or
            `None`.

    Returns:
        UTF-8 text with undecodable bytes replaced.
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _quote(value: str) -> str:
    """Quote a shell fragment for safe insertion into a shell command.

    Args:
        value: Raw string to quote.

    Returns:
        Shell-escaped string.
    """
    return shlex.quote(value)


def _is_modal_auth_error(exc: Exception, modal: object | None = None) -> bool:
    """Return whether an exception is Modal's configured auth error type.

    Args:
        exc: Exception raised by Modal or the provider.
        modal: Optional Modal module object. When omitted, Modal is loaded
            lazily.

    Returns:
        `True` when the exception is recognized as a Modal auth failure.
    """
    if modal is None:
        try:
            modal = ModalSandboxProvider._load_modal()
        except RuntimeError:
            return False

    auth_error = getattr(getattr(modal, "exception", None), "AuthError", None)
    return isinstance(exc, auth_error) if isinstance(auth_error, type) else False


def _raise_with_auth_guidance(exc: Exception) -> None:
    """Raise a package auth error with actionable Modal setup guidance.

    Args:
        exc: Original Modal authentication exception.

    Raises:
        ModalAuthenticationError: Always raised with setup commands and the
            original Modal detail.
    """
    detail = str(exc).strip()
    message = MODAL_AUTH_GUIDANCE
    if detail:
        message = f"{message}\n\nModal error: {detail}"
    raise ModalAuthenticationError(message) from exc


def _translate_modal_auth_error(exc: Exception, modal: object | None = None) -> None:
    """Translate Modal auth failures into SDK-specific exceptions.

    Args:
        exc: Exception raised by Modal or the provider.
        modal: Optional Modal module object used for type checks.

    Raises:
        ModalAuthenticationError: If `exc` is recognized as a Modal auth error.
    """
    if _is_modal_auth_error(exc, modal):
        _raise_with_auth_guidance(exc)


def _is_modal_not_found_error(exc: Exception, modal: object | None = None) -> bool:
    """Return whether an exception is Modal's not-found error type.

    Args:
        exc: Exception raised by Modal or the provider.
        modal: Optional Modal module object. When omitted, Modal is loaded
            lazily.

    Returns:
        `True` when the exception is recognized as Modal's not-found error.
    """
    if modal is None:
        try:
            modal = ModalSandboxProvider._load_modal()
        except RuntimeError:
            return False

    not_found_error = getattr(getattr(modal, "exception", None), "NotFoundError", None)
    return isinstance(exc, not_found_error) if isinstance(not_found_error, type) else False


def _raise_provider_error(exc: Exception, *, context: str | None = None) -> NoReturn:
    """Raise a provider error with optional operation context.

    Args:
        exc: Original provider exception.
        context: Human-readable operation, such as "running shell command".

    Raises:
        SandboxProviderError: Always raised with the original exception chained.
    """
    detail = str(exc) or exc.__class__.__name__
    if context:
        detail = f"{context}: {detail}"
    raise SandboxProviderError(detail) from exc


def _truncate_text(value: str, max_bytes: int | None) -> tuple[str, bool]:
    """Apply an output byte cap to a text stream.

    Args:
        value: Text to cap.
        max_bytes: Maximum encoded UTF-8 bytes, or `None` for no cap.

    Returns:
        Tuple of possibly truncated text and whether truncation occurred.

    Raises:
        ValueError: If `max_bytes` is negative.
    """
    if max_bytes is None:
        return value, False
    if max_bytes < 0:
        raise ValueError("max_output_bytes must be non-negative or None.")

    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value, False
    return encoded[:max_bytes].decode("utf-8", errors="ignore"), True


def _argv_command(cmd: str, args: Sequence[str] | None = None) -> tuple[str, tuple[str, ...]]:
    """Build display text and normalized args for an argv command.

    Args:
        cmd: Executable name or path.
        args: Optional command arguments.

    Returns:
        Shell-style display command and tuple of string arguments.
    """
    command_args = tuple(str(arg) for arg in (args or ()))
    return shlex.join([cmd, *command_args]), command_args


def sandbox_path(path: str, workspace: str) -> str:
    """Convert relative SDK paths into absolute sandbox paths.

    Args:
        path: Relative workspace path, or absolute sandbox path.
        workspace: Absolute sandbox workspace root.

    Returns:
        Absolute path inside the sandbox.

    Raises:
        ValueError: If a relative path attempts to escape the workspace.
    """
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


def sandbox_workdir(cwd: str | None, default_workdir: str | None, workspace: str) -> str:
    """Resolve a command working directory inside the sandbox.

    Args:
        cwd: Per-command working directory.
        default_workdir: Sandbox default working directory.
        workspace: Absolute sandbox workspace root.

    Returns:
        Absolute working directory inside the sandbox.

    Raises:
        ValueError: If a relative working directory escapes the workspace.
    """
    return sandbox_path(cwd or default_workdir or workspace, workspace)


class ModalSandboxProvider:
    """Provider backed by real Modal Sandbox objects."""

    def __init__(self, sandbox: Any, config: SandboxConfig, *, owns_sandbox: bool = True):
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
            image = _resolve_image(modal, config.image)
            if image is not None:
                create_kwargs["image"] = image

            volumes = _resolve_volumes(modal, volumes=config.volumes)
            if volumes:
                create_kwargs["volumes"] = volumes

            readiness_probe = _resolve_readiness_probe(modal, config.readiness_probe)
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
            _translate_modal_auth_error(exc, modal)
            _raise_provider_error(exc, context="creating Modal sandbox")
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
            _translate_modal_auth_error(exc, modal)
            if _is_modal_not_found_error(exc, modal):
                raise SandboxNotFoundError(
                    f"No running Modal sandbox named {name!r} was found in app {config.app_name!r}."
                ) from exc
            _raise_provider_error(exc, context=f"attaching to Modal sandbox named {name}")
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
            _translate_modal_auth_error(exc, modal)
            _raise_provider_error(exc, context=f"attaching to Modal sandbox {sandbox_id}")
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
    def filesystem(self) -> Any:
        """Return Modal's native sandbox filesystem API.

        Returns:
            Provider-specific filesystem object used for file operations.
        """
        return self._sandbox.filesystem

    @property
    def sandbox_id(self) -> str | None:
        """Return the Modal sandbox object ID when available.

        Returns:
            Sandbox object ID, or `None` if Modal has not exposed one.
        """
        value = getattr(self._sandbox, "object_id", None) or getattr(self._sandbox, "sandbox_id", None)
        return str(value) if value is not None else None

    def _modal_call(self, operation: Callable[[], T], *, context: str | None = None, max_attempts: int = 3) -> T:  # type: ignore
        """Run a Modal filesystem operation with SDK error translation and retry.

        Retries up to `max_attempts` times on transient network errors with
        exponential backoff. Auth errors are never retried.

        Args:
            operation: Zero-argument callable that performs the Modal action.
            context: Optional operation description for error messages.
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
                _translate_modal_auth_error(exc)
                if attempt < max_attempts - 1 and _is_transient_error(exc):
                    time.sleep(delay * (2**attempt))
                    continue
                _raise_provider_error(exc, context=context)

    def run(
        self,
        command: str,
        timeout: int | None = None,
        cwd: str | None = None,
        max_output_bytes: int | None = None,
    ) -> CommandResult:
        """Run a shell command inside the Modal sandbox.

        Args:
            command: Shell command to execute.
            timeout: Optional command timeout in seconds.
            cwd: Optional working directory inside the sandbox.
            max_output_bytes: Optional per-call output guard in bytes.

        Returns:
            Command result with captured output and timing metadata.
        """
        effective_timeout = timeout if timeout is not None else self.config.command_timeout
        effective_cwd = sandbox_workdir(cwd, self.config.workdir, self.config.workspace)
        effective_max_output_bytes = max_output_bytes if max_output_bytes is not None else self.config.max_output_bytes
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
        except Exception as exc:
            _translate_modal_auth_error(exc)
            _raise_provider_error(exc, context="running shell command")
        duration_ms = int((time.monotonic() - start) * 1000)
        stdout, stdout_truncated = _truncate_text(stdout, effective_max_output_bytes)
        stderr, stderr_truncated = _truncate_text(stderr, effective_max_output_bytes)

        return CommandResult(
            command=command,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=duration_ms,
            timed_out=timed_out,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            max_output_bytes=effective_max_output_bytes,
        )

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
            Command result with captured output and timing metadata.
        """
        command, command_args = _argv_command(cmd, args)
        effective_timeout = timeout if timeout is not None else self.config.command_timeout
        effective_cwd = sandbox_workdir(cwd, self.config.workdir, self.config.workspace)
        effective_max_output_bytes = max_output_bytes if max_output_bytes is not None else self.config.max_output_bytes

        start = time.monotonic()
        stdout = ""
        stderr = ""
        exit_code: int | None = None
        timed_out = False
        try:
            process = self._sandbox.exec(
                cmd,
                *command_args,
                timeout=effective_timeout,
                workdir=effective_cwd,
                env=dict(env) if env is not None else None,
            )
            stdout = _decode_stream(process.stdout.read())
            stderr = _decode_stream(process.stderr.read())
            process.wait()
            exit_code = getattr(process, "returncode", None)
        except TimeoutError as exc:
            timed_out = True
            stderr = str(exc)
        except Exception as exc:
            _translate_modal_auth_error(exc)
            _raise_provider_error(exc, context="running argv command")
        duration_ms = int((time.monotonic() - start) * 1000)
        stdout, stdout_truncated = _truncate_text(stdout, effective_max_output_bytes)
        stderr, stderr_truncated = _truncate_text(stderr, effective_max_output_bytes)

        return CommandResult(
            command=command,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=duration_ms,
            timed_out=timed_out,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            max_output_bytes=effective_max_output_bytes,
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
        """Start an argv-style command and return a process handle.

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
        command_args = tuple(str(arg) for arg in (args or ()))
        effective_timeout = timeout
        effective_cwd = sandbox_workdir(cwd, self.config.workdir, self.config.workspace)
        try:
            process = self._sandbox.exec(
                cmd,
                *command_args,
                timeout=effective_timeout,
                workdir=effective_cwd,
                env=dict(env) if env is not None else None,
                pty=pty,
            )
        except Exception as exc:
            _translate_modal_auth_error(exc)
            _raise_provider_error(exc, context="starting detached command")
        return SandboxCommand(process)

    def write_text(self, path: str, content: str) -> None:
        """Write UTF-8 text through Modal's filesystem API.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            content: Text content to write.
        """
        remote_path = sandbox_path(path, self.config.workspace)
        self._modal_call(
            lambda: self.filesystem.write_text(content, remote_path), context=f"writing text to {remote_path}"
        )

    def write_bytes(self, path: str, content: bytes) -> None:
        """Write bytes through Modal's filesystem API.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            content: Binary content to write.
        """
        remote_path = sandbox_path(path, self.config.workspace)
        self._modal_call(
            lambda: self.filesystem.write_bytes(content, remote_path), context=f"writing bytes to {remote_path}"
        )

    def read_text(self, path: str) -> str:
        """Read UTF-8 text through Modal's filesystem API.

        Args:
            path: Relative workspace path, or absolute sandbox path.

        Returns:
            File contents as text.
        """
        remote_path = sandbox_path(path, self.config.workspace)
        return self._modal_call(
            lambda: self.filesystem.read_text(remote_path), context=f"reading text from {remote_path}"
        )

    def read_bytes(self, path: str) -> bytes:
        """Read bytes through Modal's filesystem API.

        Args:
            path: Relative workspace path, or absolute sandbox path.

        Returns:
            File contents as bytes.
        """
        remote_path = sandbox_path(path, self.config.workspace)
        return self._modal_call(
            lambda: self.filesystem.read_bytes(remote_path), context=f"reading bytes from {remote_path}"
        )

    def list_files(self, path: str = ".") -> list[str]:
        """List direct children of a sandbox directory.

        Args:
            path: Relative workspace path, or absolute sandbox path.

        Returns:
            Sorted file and directory names.
        """
        remote_path = sandbox_path(path, self.config.workspace)
        entries = self._modal_call(
            lambda: self.filesystem.list_files(remote_path), context=f"listing files in {remote_path}"
        )
        return sorted(str(getattr(entry, "name", entry)) for entry in entries)

    def mkdir(self, path: str, *, parents: bool = True) -> None:
        """Create a sandbox directory.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            parents: Whether to create missing parent directories.
        """
        remote_path = sandbox_path(path, self.config.workspace)
        self._modal_call(
            lambda: self.filesystem.make_directory(remote_path, create_parents=parents),
            context=f"creating directory {remote_path}",
        )

    def remove(self, path: str, *, recursive: bool = False) -> None:
        """Remove a sandbox file or directory.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            recursive: Whether to remove directories recursively.
        """
        remote_path = sandbox_path(path, self.config.workspace)
        self._modal_call(
            lambda: self.filesystem.remove(remote_path, recursive=recursive), context=f"removing {remote_path}"
        )

    def copy_from_local(self, local_path: str | os.PathLike[str], remote_path: str) -> None:
        """Copy local data into the sandbox.

        Args:
            local_path: Local filesystem path.
            remote_path: Relative workspace path, or absolute sandbox path.
        """
        resolved_remote_path = sandbox_path(remote_path, self.config.workspace)
        self._modal_call(
            lambda: self.filesystem.copy_from_local(Path(local_path), resolved_remote_path),
            context=f"copying local path to {resolved_remote_path}",
        )

    def copy_to_local(self, remote_path: str, local_path: str | os.PathLike[str]) -> None:
        """Copy sandbox data to the local filesystem.

        Args:
            remote_path: Relative workspace path, or absolute sandbox path.
            local_path: Local filesystem destination path.
        """
        resolved_remote_path = sandbox_path(remote_path, self.config.workspace)
        self._modal_call(
            lambda: self.filesystem.copy_to_local(resolved_remote_path, Path(local_path)),
            context=f"copying sandbox path {resolved_remote_path} to local path",
        )

    def detach(self) -> None:
        """Detach from the Modal sandbox without terminating it."""
        detach = getattr(self._sandbox, "detach", None)
        try:
            if callable(detach):
                detach()
            self._owns_sandbox = False
            self._closed = True
        except Exception as exc:
            _translate_modal_auth_error(exc)
            _raise_provider_error(exc, context="detaching Modal sandbox")

    def terminate(self, *, wait: bool = True) -> None:
        """Terminate the Modal sandbox.

        Args:
            wait: Whether to wait for Modal termination to complete.
        """
        terminate = getattr(self._sandbox, "terminate", None)
        try:
            if callable(terminate):
                terminate(wait=wait)
            self._owns_sandbox = False
            self._closed = True
        except Exception as exc:
            _translate_modal_auth_error(exc)
            _raise_provider_error(exc, context="terminating Modal sandbox")

    def domain(self, port: int) -> str:
        """Return the public HTTPS URL for a declared sandbox port.

        Args:
            port: Port declared when the sandbox was created.

        Returns:
            Public URL for the Modal tunnel.
        """
        try:
            tunnels = self._sandbox.tunnels()
            tunnel = tunnels.get(port)
            if tunnel is None:
                raise ValueError(f"No tunnel is available for port {port}.")
            return str(tunnel.url)
        except Exception as exc:
            if isinstance(exc, ValueError):
                raise
            _translate_modal_auth_error(exc)
            _raise_provider_error(exc, context=f"resolving tunnel for port {port}")

    def create_snapshot(self) -> SandboxSnapshot:
        """Return a volume-backed workspace snapshot checkpoint.

        Modal Sandbox volume writes are backed by the mounted workspace volume.
        A fresh `modal.Volume.from_name(...).commit()` is not valid here because
        Modal only allows `commit()` on a mounted volume inside a container.

        Returns:
            Snapshot metadata for the mounted workspace volume.

        Raises:
            SandboxConfigurationError: If the workspace is not backed by a
                named volume.
        """
        workspace_volume = _workspace_volume_name(self.config)
        if workspace_volume is None:
            raise SandboxConfigurationError("create_snapshot requires a string workspace volume.")

        return SandboxSnapshot(name=workspace_volume, kind="modal_volume", workspace=self.config.workspace)

    def snapshot_filesystem(self, *, timeout: int = 55, ttl: int | None = 30 * 24 * 3600) -> SandboxImageSnapshot:
        """Snapshot the sandbox filesystem into a Modal image.

        Args:
            timeout: Maximum seconds to wait for Modal's snapshot operation.
            ttl: Snapshot retention in seconds, or `None` for no expiry.

        Returns:
            JSON-friendly Modal image snapshot metadata.
        """
        image = self._modal_call(
            lambda: self._sandbox.snapshot_filesystem(timeout=timeout, ttl=ttl),
            context="snapshotting Modal sandbox filesystem",
        )
        return _image_snapshot_metadata(image, kind="modal_filesystem", path=None, ttl=ttl)

    def snapshot_directory(
        self, path: str, *, timeout: int = 55, ttl: int | None = 30 * 24 * 3600
    ) -> SandboxImageSnapshot:
        """Snapshot a sandbox directory into a Modal image.

        Args:
            path: Relative workspace path, or absolute sandbox path.
            timeout: Maximum seconds to wait for Modal's snapshot operation.
            ttl: Snapshot retention in seconds, or `None` for no expiry.

        Returns:
            JSON-friendly Modal image snapshot metadata.
        """
        remote_path = sandbox_path(path, self.config.workspace)
        image = self._modal_call(
            lambda: self._sandbox.snapshot_directory(remote_path, timeout=timeout, ttl=ttl),
            context=f"snapshotting Modal sandbox directory {remote_path}",
        )
        return _image_snapshot_metadata(image, kind="modal_directory", path=remote_path, ttl=ttl)

    def mount_image(self, path: str, image: SandboxImageSnapshot | str | object) -> None:
        """Mount a Modal image at a sandbox path.

        Args:
            path: Relative workspace path, or absolute sandbox mount path.
            image: Modal image object, image ID, or SDK image snapshot metadata.
        """
        remote_path = sandbox_path(path, self.config.workspace)
        if remote_path == "/":
            raise SandboxConfigurationError("mount_image path must not be '/'.")
        self._modal_call(
            lambda: self._sandbox.mount_image(remote_path, _resolve_mount_image(image)),
            context=f"mounting image at {remote_path}",
        )

    def unmount_image(self, path: str) -> None:
        """Unmount a Modal image from a sandbox path."""
        remote_path = sandbox_path(path, self.config.workspace)
        self._modal_call(lambda: self._sandbox.unmount_image(remote_path), context=f"unmounting image at {remote_path}")

    def stat(self, path: str) -> SandboxFileStat:
        """Return metadata for a sandbox filesystem path."""
        remote_path = sandbox_path(path, self.config.workspace)
        info = self._modal_call(lambda: self.filesystem.stat(remote_path), context=f"stating {remote_path}")
        return _file_stat_metadata(info, path=remote_path)

    def watch(
        self,
        path: str,
        *,
        recursive: bool = False,
        timeout: int | None = None,
        filter: Sequence[str] | None = None,
    ) -> list[SandboxWatchEvent]:
        """Return filesystem watch events for a sandbox path.

        The provider consumes Modal's iterator into a list so the CLI can emit
        a bounded JSON response when `timeout` is provided.
        """
        remote_path = sandbox_path(path, self.config.workspace)
        resolved_filter = _resolve_watch_filters(filter)
        try:
            events = self.filesystem.watch(
                remote_path,
                recursive=recursive,
                timeout=timeout,
                filter=resolved_filter,
            )
            normalized_events: list[SandboxWatchEvent] = []
            for event in events:
                normalized_events.extend(_file_watch_events(event))
            return normalized_events
        except Exception as exc:
            _translate_modal_auth_error(exc)
            _raise_provider_error(exc, context=f"watching {remote_path}")

    def sync_workspace(self) -> CommandResult:
        """Persist workspace-volume changes without waiting for termination."""
        if _workspace_volume_name(self.config) is None:
            raise SandboxConfigurationError("sync_workspace requires a string workspace volume.")
        return self.run_command("sync", [self.config.workspace])

    def wait_until_ready(self, *, timeout: int = 300) -> None:
        """Wait until the sandbox readiness probe succeeds."""
        self._modal_call(
            lambda: self._sandbox.wait_until_ready(timeout=timeout),
            context="waiting for Modal sandbox readiness",
        )

    def close(self) -> None:
        """Terminate or detach from the Modal sandbox.

        Created providers own their sandbox and terminate it on close. Attached
        providers only detach so the caller's existing sandbox keeps running.
        """
        if self._closed:
            return
        if self._owns_sandbox:
            self.terminate(wait=True)
        else:
            self.detach()


def _resolve_image(modal: Any, image: ImageSpec) -> object | None:
    """Resolve public image input into a Modal image object.

    Args:
        modal: Imported Modal module.
        image: Registry tag, Modal image object, or `None`.

    Returns:
        Modal image object, pass-through object, or `None`.
    """
    if image is None:
        return None
    if isinstance(image, str):
        return modal.Image.from_registry(image)
    return image


def _resolve_volumes(
    modal: Any,
    *,
    volumes: Sequence[SandboxVolume],
) -> dict[str, object]:
    """Build Modal's mount-path-to-volume mapping.

    Args:
        modal: Imported Modal module.
        volumes: SDK volume declarations.

    Returns:
        Mapping accepted by `modal.Sandbox.create(volumes=...)`.
    """
    resolved: dict[str, object] = {}
    for volume in volumes:
        resolved[volume.mount_path] = _resolve_volume(
            modal,
            volume.volume,
            create_if_missing=volume.create_if_missing,
        )
    return resolved


def _resolve_readiness_probe(modal: Any, probe: object | None) -> object | None:
    """Resolve a public readiness probe spec into a Modal Probe object."""
    if probe is None:
        return None
    if isinstance(probe, SandboxReadinessProbe):
        if probe.kind == "tcp":
            if probe.port is None:
                raise SandboxConfigurationError("TCP readiness probe requires a port.")
            return modal.Probe.with_tcp(probe.port, interval_ms=probe.interval_ms)
        if probe.kind == "exec":
            return modal.Probe.with_exec(*probe.command, interval_ms=probe.interval_ms)
        raise SandboxConfigurationError(f"Unsupported readiness probe kind {probe.kind!r}.")
    return probe


def _workspace_volume_name(config: SandboxConfig) -> str | None:
    """Find the named volume mounted at the configured workspace.

    Args:
        config: Effective sandbox configuration.

    Returns:
        Workspace volume name, or `None` when the workspace is not backed by a
        named volume.
    """
    workspace = config.workspace.rstrip("/") or "/"
    for volume in config.volumes:
        mount_path = volume.mount_path.rstrip("/") or "/"
        if mount_path == workspace and isinstance(volume.volume, str):
            return volume.volume
    return None


def _image_snapshot_metadata(
    image: object,
    *,
    kind: str,
    path: str | None,
    ttl: int | None,
) -> SandboxImageSnapshot:
    """Normalize a Modal image snapshot object into SDK metadata."""
    image_id = getattr(image, "object_id", None) or getattr(image, "image_id", None)
    if image_id is None:
        raise SandboxProviderError("Modal snapshot image did not expose an object ID.")
    return SandboxImageSnapshot(image_id=str(image_id), kind=kind, path=path, ttl_seconds=ttl)


def _resolve_mount_image(image: SandboxImageSnapshot | str | object) -> object:
    """Resolve SDK image metadata or an image ID into a Modal Image object."""
    if isinstance(image, SandboxImageSnapshot):
        image = image.image_id
    if isinstance(image, str):
        modal = ModalSandboxProvider._load_modal()
        from_id = getattr(modal.Image, "from_id", None)
        if not callable(from_id):
            raise SandboxProviderError("Installed Modal SDK does not expose Image.from_id.")
        return from_id(image)
    return image


def _file_stat_metadata(info: object, *, path: str) -> SandboxFileStat:
    """Normalize Modal FileInfo-like objects into SDK metadata."""
    kind_value = getattr(info, "type", None)
    kind = getattr(kind_value, "value", kind_value)
    modified_time = getattr(info, "modified_time", None)
    if isinstance(modified_time, datetime):
        modified = modified_time.isoformat()
    elif modified_time is None:
        modified = None
    else:
        modified = str(modified_time)
    size = getattr(info, "size", None)
    return SandboxFileStat(
        path=path,
        kind=str(kind) if kind is not None else "unknown",
        size=int(size) if size is not None else None,
        permissions=str(getattr(info, "permissions", "")) or None,
        modified_time=modified,
    )


def _file_watch_events(event: object) -> list[SandboxWatchEvent]:
    """Normalize Modal FileWatchEvent-like objects into SDK metadata."""
    raw_paths = getattr(event, "paths", None)
    if raw_paths:
        paths = [str(path) for path in raw_paths]
    else:
        raw_path = getattr(event, "path", None) or getattr(event, "src_path", None) or getattr(event, "name", None)
        paths = [str(raw_path) if raw_path is not None else ""]
    raw_type = getattr(event, "type", None) or getattr(event, "event_type", None)
    event_type = getattr(raw_type, "value", raw_type)
    normalized_type = str(event_type) if event_type is not None else "unknown"
    return [SandboxWatchEvent(path=path, event_type=normalized_type) for path in paths]


def _resolve_watch_filters(filters: Sequence[str] | None) -> list[object] | None:
    """Resolve optional watch-event filter names into Modal enum values."""
    if filters is None:
        return None
    try:
        event_type = import_module("modal.file_io").FileWatchEventType
    except Exception:
        return [str(item) for item in filters]

    resolved: list[object] = []
    for item in filters:
        name = str(item).strip()
        for candidate in (name, name.capitalize(), name.upper(), name.lower()):
            value = getattr(event_type, candidate, None)
            if value is not None:
                resolved.append(value)
                break
        else:
            raise SandboxConfigurationError(f"Unsupported watch event type {item!r}.")
    return resolved


def _resolve_volume(modal: Any, volume: VolumeSpec, *, create_if_missing: bool = True) -> object:
    """Resolve public volume input into a Modal volume object.

    Args:
        modal: Imported Modal module.
        volume: Modal volume name or prebuilt volume-like object.
        create_if_missing: Whether Modal should create named volumes.

    Returns:
        Modal volume object or the original prebuilt volume object.
    """
    if isinstance(volume, str):
        return modal.Volume.from_name(volume, create_if_missing=create_if_missing)
    return volume
