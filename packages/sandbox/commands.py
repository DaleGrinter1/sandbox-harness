"""Command result and detached process helpers for sandbox execution."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import asdict
from typing import Any

from pydantic.dataclasses import dataclass


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
        stdout_truncated: Whether stdout was truncated by the output guard.
        stderr_truncated: Whether stderr was truncated by the output guard.
        max_output_bytes: Maximum bytes allowed per output stream.
    """

    command: str
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: int
    timed_out: bool = False
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    max_output_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the result into a JSON-serializable dictionary.

        Returns:
            Dictionary with the same fields as the dataclass, suitable for CLI
            JSON output.
        """
        return asdict(self)


class SandboxCommand:
    """Wrapper around a detached sandbox command process.

    The wrapped object is normally a Modal process handle. This class keeps the
    public API small while allowing tests to pass fake process objects.
    """

    def __init__(self, process: Any):
        """Initialize the command wrapper.

        Args:
            process: Provider-specific process handle with stdout, stderr,
                wait, and optional poll/returncode attributes.
        """
        self._process = process

    @property
    def stdout(self) -> Any:
        """Return the process stdout stream.

        Returns:
            Provider-specific stdout stream object.
        """
        return self._process.stdout

    @property
    def stderr(self) -> Any:
        """Return the process stderr stream.

        Returns:
            Provider-specific stderr stream object.
        """
        return self._process.stderr

    @property
    def returncode(self) -> int | None:
        """Return the process return code when available.

        Returns:
            Process return code, or `None` if the provider does not expose one.
        """
        value = getattr(self._process, "returncode", None)
        return int(value) if value is not None else None

    def logs(self, stream: str = "stdout") -> Iterator[str]:
        """Yield text log chunks from stdout or stderr.

        Args:
            stream: Stream name to read. Must be `stdout` or `stderr`.

        Yields:
            Decoded text chunks from the selected process stream.

        Raises:
            ValueError: If `stream` is not `stdout` or `stderr`.
        """
        if stream not in {"stdout", "stderr"}:
            raise ValueError("stream must be 'stdout' or 'stderr'.")
        source = getattr(self._process, stream)
        if hasattr(source, "__iter__"):
            for chunk in source:
                yield _decode_log_chunk(chunk)
            return
        read = getattr(source, "read", None)
        if callable(read):
            value = read()
            if value:
                yield _decode_log_chunk(value)

    def wait(self) -> int | None:
        """Wait for the command to complete and return its exit code.

        Returns:
            Process exit code when the provider exposes one, otherwise `None`.
        """
        result = self._process.wait()
        if result is not None:
            return int(result)
        return self.returncode

    def poll(self) -> int | None:
        """Poll the command return code without blocking.

        Returns:
            Process exit code if the command has completed, otherwise `None`.
        """
        poll = getattr(self._process, "poll", None)
        if callable(poll):
            value = poll()
            return value if isinstance(value, int) else None
        return self.returncode


def _decode_log_chunk(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
