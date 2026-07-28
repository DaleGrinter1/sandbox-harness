from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sandbox._modal_adapters import (
    file_stat_metadata,
    file_watch_events,
    image_snapshot_metadata,
    resolve_mount_image,
    resolve_readiness_probe,
    resolve_watch_filters,
    workspace_volume_name,
)
from sandbox.errors import SandboxConfigurationError, SandboxProviderError
from sandbox.types import SandboxConfig, SandboxImageSnapshot, SandboxReadinessProbe
from sandbox.volumes import SandboxVolume


class FakeProbe:
    @staticmethod
    def with_tcp(port: int, *, interval_ms: int = 100) -> tuple[str, int, int]:
        return ("tcp", port, interval_ms)

    @staticmethod
    def with_exec(*command: str, interval_ms: int = 100) -> tuple[str, tuple[str, ...], int]:
        return ("exec", command, interval_ms)


class FakeImage:
    from_id = None


class FakeModal:
    Probe = FakeProbe
    Image = FakeImage


def test_workspace_volume_name_matches_configured_workspace() -> None:
    config = SandboxConfig(
        workspace="/work",
        volumes=(SandboxVolume(volume="work-volume", mount_path="/work"), SandboxVolume("cache", "/cache")),
    )

    assert workspace_volume_name(config) == "work-volume"


def test_readiness_probe_rejects_malformed_tcp_probe() -> None:
    probe = SandboxReadinessProbe(kind="tcp", command=())

    with pytest.raises(SandboxConfigurationError, match="requires a port"):
        resolve_readiness_probe(FakeModal, probe)


def test_image_snapshot_metadata_requires_modal_id() -> None:
    with pytest.raises(SandboxProviderError, match="object ID"):
        image_snapshot_metadata(SimpleNamespace(), kind="modal_filesystem", path=None, ttl=60)


def test_resolve_mount_image_reports_unsupported_modal_sdk() -> None:
    with pytest.raises(SandboxProviderError, match="Image.from_id"):
        resolve_mount_image(SandboxImageSnapshot("im-123", "modal_filesystem"), load_modal=lambda: FakeModal)


def test_file_metadata_and_watch_events_normalize_modal_shapes() -> None:
    stat = file_stat_metadata(
        SimpleNamespace(
            type=SimpleNamespace(value="file"),
            size="12",
            permissions="644",
            modified_time=datetime(2026, 7, 28, 1, 2, 3, tzinfo=UTC),
        ),
        path="/workspace/app.py",
    )
    events = file_watch_events(SimpleNamespace(paths=["a.py", "b.py"], type=SimpleNamespace(value="Modify")))

    assert stat.to_dict()["modified_time"] == "2026-07-28T01:02:03+00:00"
    assert [event.to_dict() for event in events] == [
        {"path": "a.py", "event_type": "Modify"},
        {"path": "b.py", "event_type": "Modify"},
    ]


def test_resolve_watch_filters_rejects_unknown_modal_enum(monkeypatch) -> None:
    monkeypatch.setattr(
        "sandbox._modal_adapters.import_module",
        lambda _: SimpleNamespace(FileWatchEventType=SimpleNamespace(Modify="Modify")),
    )

    with pytest.raises(SandboxConfigurationError, match="Unsupported watch event type"):
        resolve_watch_filters(["NotAThing"])
