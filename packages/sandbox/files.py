from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SandboxFile:
    """File content to write into a sandbox workspace."""

    path: str
    content: str | bytes
