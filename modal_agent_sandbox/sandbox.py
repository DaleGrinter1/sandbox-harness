from __future__ import annotations

from .provider_modal import (
    ModalSandboxProvider,
    SandboxProvider,
    list_command,
    read_command,
    write_command,
)
from .types import CommandResult, SandboxConfig


class Sandbox:
    def __init__(self, provider: SandboxProvider):
        self._provider = provider

    @classmethod
    def create(
        cls,
        *,
        app_name: str = "modal-agent-sandbox",
        workspace: str = "/workspace",
        default_timeout: int = 30,
        volume_name: str | None = "modal-agent-sandbox-workspace",
        use_volume: bool = True,
        sandbox_id: str | None = None,
    ) -> "Sandbox":
        config = SandboxConfig(
            app_name=app_name,
            workspace=workspace,
            default_timeout=default_timeout,
            volume_name=volume_name,
            use_volume=use_volume,
        )
        if sandbox_id:
            provider = ModalSandboxProvider.from_id(sandbox_id, config)
        else:
            provider = ModalSandboxProvider.create(config)
        return cls(provider)

    @classmethod
    def from_provider(cls, provider: SandboxProvider) -> "Sandbox":
        return cls(provider)

    @property
    def config(self) -> SandboxConfig:
        return self._provider.config

    def run(self, command: str, timeout: int | None = None, cwd: str | None = None) -> CommandResult:
        return self._provider.run(command, timeout=timeout, cwd=cwd or self.config.workspace)

    def write_file(self, path: str, content: str | bytes) -> CommandResult:
        result = self._provider.run(write_command(path, content, self.config.workspace), cwd="/")
        if self.config.use_volume:
            self._provider.run(f"sync {self.config.workspace}", timeout=10, cwd="/")
        return result

    def read_file(self, path: str) -> str:
        result = self._provider.run(read_command(path, self.config.workspace), cwd="/")
        if result.timed_out or result.exit_code not in (0, None):
            raise RuntimeError(result.stderr or f"Failed to read sandbox file: {path}")
        return result.stdout

    def list_files(self, path: str = ".") -> list[str]:
        result = self._provider.run(list_command(path, self.config.workspace), cwd="/")
        if result.timed_out or result.exit_code not in (0, None):
            raise RuntimeError(result.stderr or f"Failed to list sandbox files: {path}")
        return [line for line in result.stdout.splitlines() if line]

    def close(self) -> None:
        self._provider.close()

    def __enter__(self) -> "Sandbox":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
