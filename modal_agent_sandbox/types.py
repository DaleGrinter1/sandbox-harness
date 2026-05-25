from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SandboxConfig:
    app_name: str = "modal-agent-sandbox"
    workspace: str = "/workspace"
    default_timeout: int = 30
    volume_name: str | None = "modal-agent-sandbox-workspace"
    use_volume: bool = True


@dataclass(frozen=True)
class CommandResult:
    command: str
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: int
    timed_out: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
