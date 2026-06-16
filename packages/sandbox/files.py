"""Data types for writing files into sandbox workspaces."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SandboxFile:
    """File content to write into a sandbox workspace.

    Attributes:
        path: Relative workspace path, or absolute path inside the sandbox.
        content: Text or bytes to write at `path`.
    """

    path: str
    content: str | bytes
