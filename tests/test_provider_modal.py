from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from sandbox.errors import ModalAuthenticationError, SandboxProviderError
from sandbox.provider_modal import ModalSandboxProvider, sandbox_path
from sandbox.types import SandboxConfig
from sandbox.volumes import SandboxVolume


class FakeAuthError(Exception):
    pass


class FakeStream:
    def __init__(self, value: str):
        self.value = value

    def read(self) -> str:
        return self.value


class FakeProcess:
    def __init__(self, stdout: str = "ok\n", stderr: str = "") -> None:
        self.stdout = FakeStream(stdout)
        self.stderr = FakeStream(stderr)
        self.returncode: int | None = 0

    def wait(self) -> int | None:
        return self.returncode

    def poll(self) -> int | None:
        return self.returncode


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
        self.object_id = "sb-created"
        self.filesystem = FakeFilesystem()
        self.exec_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.raise_auth_error_on_exec = False
        self.raise_runtime_error_on_exec = False
        self.stdout = "ok\n"
        self.stderr = ""
        self.terminated = False
        self.detached = False
        self.tunnel_map: dict[int, object] = {3000: SimpleNamespace(url="https://sandbox.example")}

    def exec(self, *args: object, **kwargs: object) -> FakeProcess:
        if self.raise_auth_error_on_exec:
            raise FakeAuthError("token missing")
        if self.raise_runtime_error_on_exec:
            raise RuntimeError("provider failed")
        self.exec_calls.append((args, kwargs))
        return FakeProcess(stdout=self.stdout, stderr=self.stderr)

    def tunnels(self) -> dict[int, object]:
        return self.tunnel_map

    def terminate(self, *, wait: bool = True) -> None:
        self.terminated = wait

    def detach(self) -> None:
        self.detached = True


class FakeImage:
    @staticmethod
    def from_registry(tag: str) -> tuple[str, str]:
        return ("image", tag)


class FakeVolume:
    commits: list[str] = []

    def __init__(self, name: str) -> None:
        self.name = name

    @staticmethod
    def from_name(name: str, *, create_if_missing: bool = False) -> object:
        if create_if_missing:
            return ("volume", name, create_if_missing)
        return FakeVolume(name)

    def commit(self) -> None:
        self.commits.append(self.name)


class FakeApp:
    lookups: list[tuple[str, bool]] = []
    raise_auth_error = False

    @staticmethod
    def lookup(name: str, *, create_if_missing: bool = False) -> tuple[str, str]:
        if FakeApp.raise_auth_error:
            raise FakeAuthError("token missing")
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
        sandbox.object_id = sandbox_id
        FakeModalSandbox.attached_sandbox = sandbox
        return sandbox


class FakeModal:
    App = FakeApp
    Image = FakeImage
    Volume = FakeVolume
    Sandbox = FakeModalSandbox
    exception = SimpleNamespace(AuthError=FakeAuthError)


def use_fake_modal(monkeypatch) -> None:
    FakeApp.lookups = []
    FakeApp.raise_auth_error = False
    FakeVolume.commits = []
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
            volumes=(
                SandboxVolume.workspace("workspace-volume"),
                SandboxVolume(volume="cache-volume", mount_path="/cache"),
                SandboxVolume(volume="data-volume", mount_path="/data", create_if_missing=False),
            ),
            env={"A": "B"},
            workdir="/workspace",
            cpu=2.0,
            memory=512,
            gpu="T4",
            region="us-east-1",
            block_network=True,
            encrypted_ports=(3000,),
            unencrypted_ports=(9229,),
        )
    )

    kwargs = FakeModalSandbox.created_kwargs
    volumes = cast(dict[str, object], kwargs["volumes"])
    assert kwargs["image"] == ("image", "python:3.13-slim")
    assert volumes["/workspace"] == ("volume", "workspace-volume", True)
    assert volumes["/cache"] == ("volume", "cache-volume", True)
    assert isinstance(volumes["/data"], FakeVolume)
    assert volumes["/data"].name == "data-volume"
    assert volumes == {
        "/workspace": ("volume", "workspace-volume", True),
        "/cache": ("volume", "cache-volume", True),
        "/data": volumes["/data"],
    }
    assert kwargs["env"] == {"A": "B"}
    assert kwargs["workdir"] == "/workspace"
    assert kwargs["cpu"] == 2.0
    assert kwargs["memory"] == 512
    assert kwargs["gpu"] == "T4"
    assert kwargs["region"] == "us-east-1"
    assert kwargs["block_network"] is True
    assert kwargs["encrypted_ports"] == [3000]
    assert kwargs["unencrypted_ports"] == [9229]


def test_create_passes_modal_image_objects_through(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    image = object()

    ModalSandboxProvider.create(SandboxConfig(image=image))

    assert FakeModalSandbox.created_kwargs["image"] is image


def test_create_auth_error_guides_user_through_modal_setup(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    FakeApp.raise_auth_error = True

    with pytest.raises(ModalAuthenticationError) as exc:
        ModalSandboxProvider.create(SandboxConfig())

    message = str(exc.value)
    assert "modal setup" in message
    assert "python -m modal setup" in message
    assert "MODAL_TOKEN_ID" in message
    assert "token missing" in message


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


def test_provider_exposes_sandbox_id_and_explicit_lifecycle_methods(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig())

    assert provider.sandbox_id == "sb-created"
    provider.detach()
    assert FakeModalSandbox.created_sandbox is not None
    assert FakeModalSandbox.created_sandbox.detached is True
    assert FakeModalSandbox.created_sandbox.terminated is False

    provider.terminate(wait=True)
    assert FakeModalSandbox.created_sandbox.terminated is True


def test_from_id_can_skip_workspace_creation_for_lifecycle_commands(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.from_id("sb-123", SandboxConfig(), ensure_workspace=False)

    assert provider.sandbox_id == "sb-123"
    assert FakeModalSandbox.attached_sandbox is not None
    assert FakeModalSandbox.attached_sandbox.filesystem.calls == []


def test_run_uses_shell_in_workspace_with_command_timeout(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig(command_timeout=17))

    result = provider.run("echo ok")

    assert result.stdout == "ok\n"
    assert result.exit_code == 0
    assert result.max_output_bytes == 10 * 1024 * 1024
    assert provider._sandbox.exec_calls[-1] == (("sh", "-lc", "cd /workspace && echo ok"), {"timeout": 17})


def test_run_command_uses_argv_without_shell_wrapping(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig(command_timeout=17))

    result = provider.run_command("python", ["-c", "print(123)"], cwd="/work", env={"A": "B"}, timeout=9)

    assert result.stdout == "ok\n"
    assert result.command == "python -c 'print(123)'"
    assert provider._sandbox.exec_calls[-1] == (
        ("python", "-c", "print(123)"),
        {"timeout": 9, "workdir": "/work", "env": {"A": "B"}},
    )


def test_run_command_detached_returns_process_handle(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig(command_timeout=17))

    command = provider.run_command_detached("npm", ["run", "dev"], cwd="/work", env={"A": "B"}, pty=True)

    assert command.wait() == 0
    assert list(command.logs()) == ["ok\n"]
    assert provider._sandbox.exec_calls[-1] == (
        ("npm", "run", "dev"),
        {"timeout": 17, "workdir": "/work", "env": {"A": "B"}, "pty": True},
    )


def test_run_can_truncate_stdout_and_stderr(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig(max_output_bytes=4))
    provider._sandbox.stdout = "abcdef"
    provider._sandbox.stderr = "123456"

    result = provider.run("echo ok")

    assert result.stdout == "abcd"
    assert result.stderr == "1234"
    assert result.stdout_truncated is True
    assert result.stderr_truncated is True
    assert result.max_output_bytes == 4


def test_run_per_call_max_output_bytes_overrides_config(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig(max_output_bytes=10))
    provider._sandbox.stdout = "abcdef"

    result = provider.run("echo ok", max_output_bytes=3)

    assert result.stdout == "abc"
    assert result.stdout_truncated is True
    assert result.max_output_bytes == 3


def test_run_does_not_truncate_under_output_limit(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig(max_output_bytes=10))
    provider._sandbox.stdout = "abc"

    result = provider.run("echo ok")

    assert result.stdout == "abc"
    assert result.stdout_truncated is False


def test_domain_returns_tunnel_url(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig())

    assert provider.domain(3000) == "https://sandbox.example"


def test_domain_raises_for_missing_tunnel(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig())

    with pytest.raises(ValueError, match="No tunnel"):
        provider.domain(8080)


def test_create_snapshot_returns_workspace_volume_metadata(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig(volumes=(SandboxVolume.workspace("snapshot-volume"),)))

    snapshot = provider.create_snapshot()

    assert snapshot.name == "snapshot-volume"
    assert snapshot.kind == "modal_volume"
    assert snapshot.workspace == "/workspace"
    assert FakeVolume.commits == []


def test_create_snapshot_uses_first_class_workspace_volume(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig(volumes=(SandboxVolume.workspace("snapshot-volume"),)))

    snapshot = provider.create_snapshot()

    assert snapshot.name == "snapshot-volume"
    assert snapshot.kind == "modal_volume"
    assert snapshot.workspace == "/workspace"
    assert FakeVolume.commits == []


def test_create_snapshot_requires_string_workspace_volume(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    provider = ModalSandboxProvider.create(SandboxConfig())

    with pytest.raises(ValueError, match="workspace volume"):
        provider.create_snapshot()


def test_run_auth_error_guides_user_through_modal_setup(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    sandbox = FakeSandboxObject()
    sandbox.raise_auth_error_on_exec = True
    provider = ModalSandboxProvider(sandbox, SandboxConfig())

    with pytest.raises(ModalAuthenticationError) as exc:
        provider.run("echo ok")

    assert "modal setup" in str(exc.value)
    assert "MODAL_TOKEN_SECRET" in str(exc.value)


def test_run_wraps_unexpected_provider_errors(monkeypatch) -> None:
    use_fake_modal(monkeypatch)
    sandbox = FakeSandboxObject()
    sandbox.raise_runtime_error_on_exec = True
    provider = ModalSandboxProvider(sandbox, SandboxConfig())

    with pytest.raises(SandboxProviderError, match="provider failed"):
        provider.run("echo ok")


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
