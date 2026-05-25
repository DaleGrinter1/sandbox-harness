from __future__ import annotations

import base64
import shlex
import time
from dataclasses import replace
from typing import Protocol

from .types import CommandResult, SandboxConfig


class SandboxProvider(Protocol):
    config: SandboxConfig

    def run(self, command: str, timeout: int | None = None, cwd: str | None = None) -> CommandResult:
        ...

    def close(self) -> None:
        ...


def _decode_stream(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _quote(value: str) -> str:
    return shlex.quote(value)


def _inside_workspace(path: str, workspace: str) -> str:
    if path.startswith("/"):
        return path
    return f"{workspace.rstrip('/')}/{path}"


class ModalSandboxProvider:
    def __init__(self, sandbox: object, config: SandboxConfig):
        self._sandbox = sandbox
        self.config = config

    @classmethod
    def create(cls, config: SandboxConfig | None = None) -> "ModalSandboxProvider":
        config = config or SandboxConfig()
        try:
            import modal
        except ImportError as exc:
            raise RuntimeError("Install the 'modal' package to use Modal sandboxes.") from exc

        app = modal.App.lookup(config.app_name, create_if_missing=True)
        volumes = None
        if config.use_volume and config.volume_name:
            volume = modal.Volume.from_name(config.volume_name, create_if_missing=True)
            volumes = {config.workspace: volume}

        sandbox = modal.Sandbox.create(app=app, volumes=volumes)
        provider = cls(sandbox, config)
        provider.run(f"mkdir -p {_quote(config.workspace)}", timeout=10, cwd="/")
        return provider

    @classmethod
    def from_id(
        cls,
        sandbox_id: str,
        config: SandboxConfig | None = None,
    ) -> "ModalSandboxProvider":
        config = config or SandboxConfig()
        try:
            import modal
        except ImportError as exc:
            raise RuntimeError("Install the 'modal' package to attach to Modal sandboxes.") from exc

        return cls(modal.Sandbox.from_id(sandbox_id), config)

    def run(self, command: str, timeout: int | None = None, cwd: str | None = None) -> CommandResult:
        effective_timeout = timeout if timeout is not None else self.config.default_timeout
        effective_cwd = cwd or self.config.workspace
        shell_command = f"cd {_quote(effective_cwd)} && {command}"

        start = time.monotonic()
        timed_out = False
        stdout = ""
        stderr = ""
        exit_code: int | None = None
        try:
            process = self._sandbox.exec("bash", "-lc", shell_command, timeout=effective_timeout)
            stdout = _decode_stream(process.stdout.read())
            stderr = _decode_stream(process.stderr.read())
            process.wait()
            exit_code = getattr(process, "returncode", None)
        except TimeoutError as exc:
            timed_out = True
            stderr = str(exc)
        duration_ms = int((time.monotonic() - start) * 1000)

        return CommandResult(
            command=command,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=duration_ms,
            timed_out=timed_out,
        )

    def close(self) -> None:
        terminate = getattr(self._sandbox, "terminate", None)
        detach = getattr(self._sandbox, "detach", None)
        if callable(terminate):
            terminate(wait=True)
        if callable(detach):
            detach()

    def with_config(self, **updates: object) -> "ModalSandboxProvider":
        return ModalSandboxProvider(self._sandbox, replace(self.config, **updates))


def sandbox_path(path: str, workspace: str) -> str:
    return _inside_workspace(path, workspace)


def write_command(path: str, content: str | bytes, workspace: str) -> str:
    target = sandbox_path(path, workspace)
    raw = content.encode("utf-8") if isinstance(content, str) else content
    encoded = base64.b64encode(raw).decode("ascii")
    encoded_path = base64.b64encode(target.encode("utf-8")).decode("ascii")
    parent = _quote(target.rsplit("/", 1)[0] or "/")
    return (
        f"mkdir -p {parent} && "
        f"python -c \"import base64, pathlib; "
        f"path = base64.b64decode({encoded_path!r}).decode('utf-8'); "
        f"pathlib.Path(path).write_bytes(base64.b64decode({encoded!r}))\""
    )


def read_command(path: str, workspace: str) -> str:
    return f"cat {_quote(sandbox_path(path, workspace))}"


def list_command(path: str, workspace: str) -> str:
    target = sandbox_path(path, workspace)
    return f"find {_quote(target)} -maxdepth 1 -mindepth 1 -printf '%f\\n' | sort"
