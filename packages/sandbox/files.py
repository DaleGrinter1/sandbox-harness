"""Data types for writing files into sandbox workspaces."""

from __future__ import annotations

from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class SandboxFile:
    """File content to write into a sandbox workspace.

    Attributes:
        path: Relative workspace path, or absolute path inside the sandbox.
        content: Text or bytes to write at `path`.
        mode: Optional POSIX file mode applied after writing, such as `0o755`.
    """

    path: str
    content: str | bytes
    mode: int | None = None
