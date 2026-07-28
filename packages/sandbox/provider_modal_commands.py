"""Command execution mixin for `ModalSandboxProvider`."""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from typing import Any

from ._modal_errors import raise_provider_error, translate_modal_auth_error
from ._modal_runtime import argv_command, decode_stream, quote, sandbox_workdir, truncate_text
from .commands import CommandResult, SandboxCommand


class ModalCommandMixin:
    """Provide command execution methods for Modal sandbox providers."""

    _sandbox: Any
    config: Any

    @staticmethod
    def _load_modal() -> Any:
        raise NotImplementedError

    def run(
        self,
        command: str,
        timeout: int | None = None,
        cwd: str | None = None,
        max_output_bytes: int | None = None,
    ) -> CommandResult:
        """Run a shell command inside the Modal sandbox."""
        effective_timeout = timeout if timeout is not None else self.config.command_timeout
        effective_cwd = sandbox_workdir(cwd, self.config.workdir, self.config.workspace)
        effective_max_output_bytes = max_output_bytes if max_output_bytes is not None else self.config.max_output_bytes
        shell_command = f"cd {quote(effective_cwd)} && {command}"

        start = time.monotonic()
        timed_out = False
        stdout = ""
        stderr = ""
        exit_code: int | None = None
        try:
            process = self._sandbox.exec("sh", "-lc", shell_command, timeout=effective_timeout)
            stdout = decode_stream(process.stdout.read())
            stderr = decode_stream(process.stderr.read())
            process.wait()
            exit_code = getattr(process, "returncode", None)
        except TimeoutError as exc:
            timed_out = True
            stderr = str(exc)
        except Exception as exc:
            translate_modal_auth_error(exc, load_modal=self._load_modal)
            raise_provider_error(exc, context="running shell command")
        duration_ms = int((time.monotonic() - start) * 1000)
        stdout, stdout_truncated = truncate_text(stdout, effective_max_output_bytes)
        stderr, stderr_truncated = truncate_text(stderr, effective_max_output_bytes)

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
        """Run an argv-style command without shell wrapping."""
        command, command_args = argv_command(cmd, args)
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
            stdout = decode_stream(process.stdout.read())
            stderr = decode_stream(process.stderr.read())
            process.wait()
            exit_code = getattr(process, "returncode", None)
        except TimeoutError as exc:
            timed_out = True
            stderr = str(exc)
        except Exception as exc:
            translate_modal_auth_error(exc, load_modal=self._load_modal)
            raise_provider_error(exc, context="running argv command")
        duration_ms = int((time.monotonic() - start) * 1000)
        stdout, stdout_truncated = truncate_text(stdout, effective_max_output_bytes)
        stderr, stderr_truncated = truncate_text(stderr, effective_max_output_bytes)

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
        """Start an argv-style command and return a process handle."""
        command_args = tuple(str(arg) for arg in (args or ()))
        effective_cwd = sandbox_workdir(cwd, self.config.workdir, self.config.workspace)
        try:
            process = self._sandbox.exec(
                cmd,
                *command_args,
                timeout=timeout,
                workdir=effective_cwd,
                env=dict(env) if env is not None else None,
                pty=pty,
            )
        except Exception as exc:
            translate_modal_auth_error(exc, load_modal=self._load_modal)
            raise_provider_error(exc, context="starting detached command")
        return SandboxCommand(process)
