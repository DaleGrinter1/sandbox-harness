from __future__ import annotations

from dataclasses import dataclass

VolumeSpec = str | object


@dataclass(frozen=True)
class SandboxVolume:
    """Volume mount requested for a sandbox.

    Attributes:
        volume: Modal volume name or prebuilt `modal.Volume` object.
        mount_path: Absolute path where the volume is mounted in the sandbox.
        create_if_missing: Whether named Modal volumes should be created when
            they do not already exist.
    """

    volume: VolumeSpec
    mount_path: str
    create_if_missing: bool = True

    @classmethod
    def workspace(
        cls,
        volume: VolumeSpec,
        *,
        workspace: str = "/workspace",
        create_if_missing: bool = True,
    ) -> SandboxVolume:
        """Build a workspace volume mount."""
        return cls(volume=volume, mount_path=workspace, create_if_missing=create_if_missing)
