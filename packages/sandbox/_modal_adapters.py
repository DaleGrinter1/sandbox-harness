"""Adapter helpers for translating SDK values to Modal SDK values."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from importlib import import_module
from typing import Any

from .errors import SandboxConfigurationError, SandboxProviderError
from .types import (
    ImageSpec,
    SandboxConfig,
    SandboxFileStat,
    SandboxImageSnapshot,
    SandboxReadinessProbe,
    SandboxWatchEvent,
)
from .volumes import SandboxVolume, VolumeSpec


def resolve_image(modal: Any, image: ImageSpec) -> object | None:
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


def resolve_volumes(
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
        resolved[volume.mount_path] = resolve_volume(
            modal,
            volume.volume,
            create_if_missing=volume.create_if_missing,
        )
    return resolved


def resolve_readiness_probe(modal: Any, probe: object | None) -> object | None:
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


def workspace_volume_name(config: SandboxConfig) -> str | None:
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


def image_snapshot_metadata(
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


def resolve_mount_image(
    image: SandboxImageSnapshot | str | object,
    *,
    load_modal: Callable[[], Any],
) -> object:
    """Resolve SDK image metadata or an image ID into a Modal Image object."""
    if isinstance(image, SandboxImageSnapshot):
        image = image.image_id
    if isinstance(image, str):
        modal = load_modal()
        from_id = getattr(modal.Image, "from_id", None)
        if not callable(from_id):
            raise SandboxProviderError("Installed Modal SDK does not expose Image.from_id.")
        return from_id(image)
    return image


def file_stat_metadata(info: object, *, path: str) -> SandboxFileStat:
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


def file_watch_events(event: object) -> list[SandboxWatchEvent]:
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


def resolve_watch_filters(filters: Sequence[str] | None) -> list[object] | None:
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


def resolve_volume(modal: Any, volume: VolumeSpec, *, create_if_missing: bool = True) -> object:
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
