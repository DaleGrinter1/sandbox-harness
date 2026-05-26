from __future__ import annotations

from types import SimpleNamespace

import pytest

from sandbox.provider_modal import ModalSandboxProvider, sandbox_path
from sandbox.types import SandboxConfig


class FakeStream:
    def __init__(self, value: str):
        self.value = value

    def read(self) -> str:
        return self.value


class FakeProcess:
    def __init__(self) -> None:
        self.stdout = FakeStream("ok\n")
        self.stderr = FakeStream("")
        self.returncode = 0

    def wait(self) -> None:
        return None


class FakeFilesystem:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def make_directory(self, remote_path: str, *, create_parents: bool = True) -> None:
        self.calls.append(("mkdir", remote_path, create_parents))

    def write_text(self, data: str, remote_path: str) -> None:
        self.calls.append(("write_text", data, remote_path))

    def write_bytes(self, data: bytes, remote_path: str) -> None:
        self.calls.append(("write_bytes", data, remote_path))

    def read_text(self, remote_path: str) -> str:
        self.calls.append(("read_text", remote_path))
        return "contents"

    def read_bytes(self, remote_path: str) -> bytes:
        self.calls.append(("read_bytes", remote_path))
        return b"contents"

    def list_files(self, remote_path: str) -> list[SimpleNamespace]:
        self.calls.append(("list_files", remote_path))
        return [SimpleNamespace(name="b.txt"), SimpleNamespace(name="a.txt")]

    def remove(self, remote_path: str, *, recursive: bool = False) -> None:
        self.calls.append(("remove", remote_path, recursive))

    def copy_from_local(self, local_path: object, remote_path: str) -> None:
        self.calls.append(("copy_from_local", str(local_path), remote_path))

    def copy_to_local(self, remote_path: str, local_path: object) -> None:
        self.calls.append(("copy_to_local", remote_path, str(local_path)))


class FakeSandboxObject:
    def __init__(self) -> None:
        self.filesystem = FakeFilesystem()
        self.exec_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.terminated = False
        self.detached = False

    def exec(self, *args: object, **kwargs: object) -> FakeProcess:
        self.exec_calls.append((args, kwargs))
        return FakeProcess()

    def terminate(self, *, wait: bool = True) -> None:
        self.terminated = wait

    def detach(self) -> None:
        self.detached = True


class FakeImage:
    @staticmethod
    def from_registry(tag: str) -> tuple[str, str]:
        return ("image", tag)


class FakeVolume:
    @staticmethod
    def from_name(name: str, *, create_if_missing: bool = False) -> tuple[str, str, bool]:
        return ("volume", name, create_if_missing)


class FakeApp:
    lookups: list[tuple[str, bool]] = []

    @staticmethod
    def lookup(name: str, *, create_if_missing: bool = False) -> tuple[str, str]:
        FakeApp.lookups.append((name, create_if_missing))
        return ("app", name)


class FakeModalSandbox:
    created_kwargs: dict[str, object] = {}
    created_sandbox: FakeSandboxObject | None = None
    attached_sandbox: FakeSandboxObject | None = None

    @classmethod
    def create(cls, **kwargs: object) -> FakeSandboxObject:
        cls.created_kwargs = kwargs
        cls.created_sandbox = FakeSandboxObject()
        return cls.created_sandbox

    @staticmethod
    def from_id(sandbox_id: str) -> FakeSandboxObject:
        sandbox = FakeSandboxObject()
        sandbox.sandbox_id = sandbox_id
        FakeModalSandbox.attached_sandbox = sandbox
        return sandbox


class FakeModal:
    App = FakeApp
    Image = FakeImage
    Volume = FakeVolume
    Sandbox = FakeModalSandbox


def use_fake_modal(monkeypatch) -> None:
    FakeApp.lookups = []
    FakeModalSandbox.created_kwargs = {}
    FakeModalSandbox.created_sandbox = None
    FakeModalSandbox.attached_sandbox = None
    monkeypatch.setattr(ModalSandboxProvider, "_load_modal", staticmethod(lambda: FakeModal))


def test_create_uses_no_default_volume(monkeypatch) -> None:
    use_fake_modal(monkeypatch)

    provider = ModalSandboxProvider.create(SandboxConfig())

    assert "volumes" not in FakeModalSandbox.created_kwargs
    assert FakeModalSandbox.created_kwargs["app"] == ("app", "modal-sandbox-sdk")
    assert provider._sandbox.filesystem.calls == [("mkdir", "/workspace", True)]


def test_create_resolves_image_and_volume_options(monkeypatch) -> None:
    use_fake_modal(monkeypatch)

    ModalSandboxProvider.create(
        SandboxConfig(
            image="python:3.13-slim",
            workspace_volume="workspace-volume",
            extra_volumes={"/cache": "cache-volume"},
            env={"A": "B"},
            workdir="/workspace",
            cpu=2.0,
            memory=512,
            gpu="T4",
            region="us-east-1",
            block_network=True,
        )
    )

    kwargs = FakeModalSandbox.created_kwargs
    assert kwargs["image"] == ("image", "python:3.13-slim")
    assert kwargs["volumes"] == {
        "/workspace": ("volume", "workspace-volume", True),
        "/cache": ("volume", "cache-volume", True),
    }
    assert kwargs["env"] == {"A": "B"}
    assert kwargs["workdir"] == "/workspace"
    assert kwargs["cpu"] == 2.0
    assert kwargs["memory"] == 512
    assert kwargs["gpu"] == "T4"
    assert kwargs["region"] == "us-east-1"
    assert kwargs["block_network"] is True


def test_create_passes_modal_image_objects_through(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    image = object()

    ModalSandboxProvider.create(SandboxConfig(image=image))

    assert FakeModalSandbox.created_kwargs["image"] is image


def test_created_provider_terminates_owned_sandbox_on_close(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig())

    provider.close()

    assert FakeModalSandbox.created_sandbox is not None
    assert FakeModalSandbox.created_sandbox.terminated is True
    assert FakeModalSandbox.created_sandbox.detached is False


def test_attached_provider_detaches_without_terminating(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.from_id("sb-123", SandboxConfig())

    provider.close()

    assert FakeModalSandbox.attached_sandbox is not None
    assert FakeModalSandbox.attached_sandbox.terminated is False
    assert FakeModalSandbox.attached_sandbox.detached is True


def test_run_uses_shell_in_workspace_with_command_timeout(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig(command_timeout=17))

    result = provider.run("echo ok")

    assert result.stdout == "ok\n"
    assert result.exit_code == 0
    assert provider._sandbox.exec_calls[-1] == (("sh", "-lc", "cd /workspace && echo ok"), {"timeout": 17})


def test_filesystem_helpers_use_workspace_paths(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig())
    fs = provider._sandbox.filesystem

    provider.write_text("notes/todo.txt", "ship it")
    provider.write_bytes("data.bin", b"data")
    assert provider.read_text("notes/todo.txt") == "contents"
    assert provider.read_bytes("data.bin") == b"contents"
    assert provider.list_files(".") == ["a.txt", "b.txt"]
    provider.remove("data.bin", recursive=False)
    provider.copy_from_local("local.txt", "remote.txt")
    provider.copy_to_local("remote.txt", "local.txt")

    assert ("write_text", "ship it", "/workspace/notes/todo.txt") in fs.calls
    assert ("write_bytes", b"data", "/workspace/data.bin") in fs.calls
    assert ("read_text", "/workspace/notes/todo.txt") in fs.calls
    assert ("read_bytes", "/workspace/data.bin") in fs.calls
    assert ("list_files", "/workspace") in fs.calls
    assert ("remove", "/workspace/data.bin", False) in fs.calls
    assert ("copy_from_local", "local.txt", "/workspace/remote.txt") in fs.calls
    assert ("copy_to_local", "/workspace/remote.txt", "local.txt") in fs.calls


def test_sandbox_path_allows_absolute_paths_and_workspace_relative_paths() -> None:
    assert sandbox_path("/tmp/file.txt", "/workspace") == "/tmp/file.txt"
    assert sandbox_path("", "/workspace") == "/workspace"
    assert sandbox_path(".", "/workspace") == "/workspace"
    assert sandbox_path("file.txt", "/workspace") == "/workspace/file.txt"
    assert sandbox_path("notes/todo.txt", "/workspace/") == "/workspace/notes/todo.txt"
    assert sandbox_path("notes/../file.txt", "/workspace") == "/workspace/file.txt"


def test_sandbox_path_rejects_relative_workspace_escapes() -> None:
    with pytest.raises(ValueError, match="escape the workspace"):
        sandbox_path("../file.txt", "/workspace")

    with pytest.raises(ValueError, match="escape the workspace"):
        sandbox_path("notes/../../file.txt", "/workspace")
