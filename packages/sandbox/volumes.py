"""Volume mount declarations for Modal Sandbox workflows."""

from __future__ import annotations

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

VolumeSpec = str | object


@dataclass(frozen=True, config=ConfigDict(arbitrary_types_allowed=True))
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
        """Build a volume mount for the sandbox workspace.

        Args:
            volume: Modal volume name or prebuilt `modal.Volume` object.
            workspace: Absolute sandbox path used as the workspace mount.
            create_if_missing: Whether Modal should create a named volume when
                it does not already exist.

        Returns:
            `SandboxVolume` mounted at `workspace`.
        """
        return cls(volume=volume, mount_path=workspace, create_if_missing=create_if_missing)
