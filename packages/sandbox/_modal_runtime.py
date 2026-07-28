"""Shared runtime helpers for the Modal sandbox provider."""

from __future__ import annotations

import shlex
from pathlib import PurePosixPath
from typing import Any


def decode_stream(value: object) -> str:
    """Normalize Modal process streams into text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def quote(value: str) -> str:
    """Quote a shell fragment for safe insertion into a shell command."""
    return shlex.quote(value)


def truncate_text(value: str, max_bytes: int | None) -> tuple[str, bool]:
    """Apply an output byte cap to a text stream."""
    if max_bytes is None:
        return value, False
    if max_bytes < 0:
        raise ValueError("max_output_bytes must be non-negative or None.")

    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value, False
    return encoded[:max_bytes].decode("utf-8", errors="ignore"), True


def argv_command(cmd: str, args: Any = None) -> tuple[str, tuple[str, ...]]:
    """Build display text and normalized args for an argv command."""
    command_args = tuple(str(arg) for arg in (args or ()))
    return shlex.join([cmd, *command_args]), command_args


def sandbox_path(path: str, workspace: str) -> str:
    """Convert relative SDK paths into absolute sandbox paths."""
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
    """Resolve a command working directory inside the sandbox."""
    return sandbox_path(cwd or default_workdir or workspace, workspace)
