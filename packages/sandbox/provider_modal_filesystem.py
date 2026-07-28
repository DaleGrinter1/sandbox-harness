"""Filesystem and snapshot mixin for `ModalSandboxProvider`."""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TypeVar, cast

from ._modal_adapters import (
    file_stat_metadata,
    file_watch_events,
    image_snapshot_metadata,
    resolve_mount_image,
    resolve_watch_filters,
    workspace_volume_name,
)
from ._modal_runtime import sandbox_path
from .errors import SandboxConfigurationError
from .types import SandboxFileStat, SandboxImageSnapshot, SandboxSnapshot, SandboxWatchEvent

T = TypeVar("T")


class ModalFilesystemMixin:
    """Provide filesystem, snapshot, and image-mount operations."""

    _sandbox: Any
    config: Any

    @staticmethod
    def _load_modal() -> Any:
        raise NotImplementedError

    def _modal_call(
        self,
        operation: Callable[[], T],
        *,
        context: str | None = None,
        retry: bool = False,
        max_attempts: int = 3,
    ) -> T:
        raise NotImplementedError

    @property
    def filesystem(self) -> Any:
        """Return Modal's native sandbox filesystem API."""
        return self._sandbox.filesystem

    def write_text(self, path: str, content: str) -> None:
        """Write UTF-8 text through Modal's filesystem API."""
        remote_path = sandbox_path(path, self.config.workspace)
        self._modal_call(
            lambda: self.filesystem.write_text(content, remote_path), context=f"writing text to {remote_path}"
        )

    def write_bytes(self, path: str, content: bytes) -> None:
        """Write bytes through Modal's filesystem API."""
        remote_path = sandbox_path(path, self.config.workspace)
        self._modal_call(
            lambda: self.filesystem.write_bytes(content, remote_path), context=f"writing bytes to {remote_path}"
        )

    def read_text(self, path: str) -> str:
        """Read UTF-8 text through Modal's filesystem API."""
        remote_path = sandbox_path(path, self.config.workspace)
        return self._modal_call(
            lambda: self.filesystem.read_text(remote_path), context=f"reading text from {remote_path}", retry=True
        )

    def read_bytes(self, path: str) -> bytes:
        """Read bytes through Modal's filesystem API."""
        remote_path = sandbox_path(path, self.config.workspace)
        return self._modal_call(
            lambda: self.filesystem.read_bytes(remote_path), context=f"reading bytes from {remote_path}", retry=True
        )

    def list_files(self, path: str = ".") -> list[str]:
        """List direct children of a sandbox directory."""
        remote_path = sandbox_path(path, self.config.workspace)
        entries = self._modal_call(
            lambda: self.filesystem.list_files(remote_path), context=f"listing files in {remote_path}", retry=True
        )
        return sorted(str(getattr(entry, "name", entry)) for entry in entries)

    def mkdir(self, path: str, *, parents: bool = True) -> None:
        """Create a sandbox directory."""
        remote_path = sandbox_path(path, self.config.workspace)
        self._modal_call(
            lambda: self.filesystem.make_directory(remote_path, create_parents=parents),
            context=f"creating directory {remote_path}",
        )

    def remove(self, path: str, *, recursive: bool = False) -> None:
        """Remove a sandbox file or directory."""
        remote_path = sandbox_path(path, self.config.workspace)
        self._modal_call(
            lambda: self.filesystem.remove(remote_path, recursive=recursive), context=f"removing {remote_path}"
        )

    def copy_from_local(self, local_path: str | os.PathLike[str], remote_path: str) -> None:
        """Copy local data into the sandbox."""
        resolved_remote_path = sandbox_path(remote_path, self.config.workspace)
        self._modal_call(
            lambda: self.filesystem.copy_from_local(Path(local_path), resolved_remote_path),
            context=f"copying local path to {resolved_remote_path}",
        )

    def copy_to_local(self, remote_path: str, local_path: str | os.PathLike[str]) -> None:
        """Copy sandbox data to the local filesystem."""
        resolved_remote_path = sandbox_path(remote_path, self.config.workspace)
        self._modal_call(
            lambda: self.filesystem.copy_to_local(resolved_remote_path, Path(local_path)),
            context=f"copying sandbox path {resolved_remote_path} to local path",
        )

    def create_snapshot(self) -> SandboxSnapshot:
        """Return a volume-backed workspace snapshot checkpoint."""
        workspace_volume = workspace_volume_name(self.config)
        if workspace_volume is None:
            raise SandboxConfigurationError("create_snapshot requires a string workspace volume.")

        return SandboxSnapshot(name=workspace_volume, kind="modal_volume", workspace=self.config.workspace)

    def snapshot_filesystem(self, *, timeout: int = 55, ttl: int | None = 30 * 24 * 3600) -> SandboxImageSnapshot:
        """Snapshot the sandbox filesystem into a Modal image."""
        image = self._modal_call(
            lambda: self._sandbox.snapshot_filesystem(timeout=timeout, ttl=ttl),
            context="snapshotting Modal sandbox filesystem",
        )
        return image_snapshot_metadata(image, kind="modal_filesystem", path=None, ttl=ttl)

    def snapshot_directory(
        self, path: str, *, timeout: int = 55, ttl: int | None = 30 * 24 * 3600
    ) -> SandboxImageSnapshot:
        """Snapshot a sandbox directory into a Modal image."""
        remote_path = sandbox_path(path, self.config.workspace)
        image = self._modal_call(
            lambda: self._sandbox.snapshot_directory(remote_path, timeout=timeout, ttl=ttl),
            context=f"snapshotting Modal sandbox directory {remote_path}",
        )
        return image_snapshot_metadata(image, kind="modal_directory", path=remote_path, ttl=ttl)

    def mount_image(self, path: str, image: SandboxImageSnapshot | str | object) -> None:
        """Mount a Modal image at a sandbox path."""
        remote_path = sandbox_path(path, self.config.workspace)
        if remote_path == "/":
            raise SandboxConfigurationError("mount_image path must not be '/'.")
        self._modal_call(
            lambda: self._sandbox.mount_image(remote_path, resolve_mount_image(image, load_modal=self._load_modal)),
            context=f"mounting image at {remote_path}",
        )

    def unmount_image(self, path: str) -> None:
        """Unmount a Modal image from a sandbox path."""
        remote_path = sandbox_path(path, self.config.workspace)
        self._modal_call(lambda: self._sandbox.unmount_image(remote_path), context=f"unmounting image at {remote_path}")

    def stat(self, path: str) -> SandboxFileStat:
        """Return metadata for a sandbox filesystem path."""
        remote_path = sandbox_path(path, self.config.workspace)
        info = self._modal_call(lambda: self.filesystem.stat(remote_path), context=f"stating {remote_path}", retry=True)
        return file_stat_metadata(info, path=remote_path)

    def watch(
        self,
        path: str,
        *,
        recursive: bool = False,
        timeout: int | None = None,
        filter: Sequence[str] | None = None,
    ) -> list[SandboxWatchEvent]:
        """Return filesystem watch events for a sandbox path."""
        remote_path = sandbox_path(path, self.config.workspace)
        resolved_filter = resolve_watch_filters(filter)
        events = self._modal_call(
            lambda: self.filesystem.watch(
                remote_path,
                recursive=recursive,
                timeout=timeout,
                filter=resolved_filter,
            ),
            context=f"watching {remote_path}",
        )
        normalized_events: list[SandboxWatchEvent] = []
        for event in events:
            normalized_events.extend(file_watch_events(event))
        return normalized_events

    def sync_workspace(self) -> Any:
        """Persist workspace-volume changes without waiting for termination."""
        if workspace_volume_name(self.config) is None:
            raise SandboxConfigurationError("sync_workspace requires a string workspace volume.")
        return cast(Any, self).run_command("sync", [self.config.workspace])
