from __future__ import annotations

import os
from collections.abc import Mapping, Sequence

import pytest
from sandbox import (
    CommandResult,
    Sandbox,
    SandboxCommand,
    SandboxConfig,
    SandboxConfigurationError,
    SandboxError,
    SandboxFile,
    SandboxNotFoundError,
    SandboxProviderError,
    SandboxSnapshot,
    SandboxVolume,
)


class FakeProvider:
    def __init__(self) -> None:
        self.config = SandboxConfig()
        self.commands: list[tuple[str, int | None, str | None]] = []
        self.argv_commands: list[
            tuple[str, tuple[str, ...], str | None, Mapping[str, str | None] | None, int | None]
        ] = []
        self.text_files = {"game.py": "print('hello')"}
        self.bytes_files = {"data.bin": b"hello"}
        self.mkdir_calls: list[tuple[str, bool]] = []
        self.remove_calls: list[tuple[str, bool]] = []
        self.copy_from_local_calls: list[tuple[str, str]] = []
        self.copy_to_local_calls: list[tuple[str, str]] = []
        self.closed = False
        self.detached = False
        self.terminated = False
        self.domain_calls: list[int] = []
        self.snapshot_created = False

    @property
    def sandbox_id(self) -> str:
        return "sb-fake"

    def run(
        self,
        command: str,
        timeout: int | None = None,
        cwd: str | None = None,
        max_output_bytes: int | None = None,
    ) -> CommandResult:
        self.commands.append((command, timeout, cwd))
        if command == "python -c 'print(123)'":
            return CommandResult(command, "123\n", "", 0, 5, max_output_bytes=max_output_bytes)
        if command == "sh -c 'exit 7'":
            return CommandResult(command, "", "", 7, 4, max_output_bytes=max_output_bytes)
        if command == "sleep 10":
            return CommandResult(
                command, "", "timed out", None, 1000, timed_out=True, max_output_bytes=max_output_bytes
            )
        return CommandResult(command, "", "", 0, 1, max_output_bytes=max_output_bytes)

    def run_command(
        self,
        cmd: str,
        args: Sequence[str] | None = None,
        *,
        cwd: str | None = None,
        env: Mapping[str, str | None] | None = None,
        timeout: int | None = None,
        max_output_bytes: int | None = None,
    ) -> CommandResult:
        command_args = tuple(args or ())
        self.argv_commands.append((cmd, command_args, cwd, env, timeout))
        return CommandResult("python -c 'print(123)'", "argv ok\n", "", 0, 2, max_output_bytes=max_output_bytes)

    def run_command_detached(
        self,
        cmd: str,
        args: Sequence[str] | None = None,
        *,
        cwd: str | None = None,
        env: Mapping[str, str | None] | None = None,
        timeout: int | None = None,
        pty: bool = False,
    ) -> SandboxCommand:
        return SandboxCommand(FakeDetachedProcess())

    def write_text(self, path: str, content: str) -> None:
        self.text_files[path] = content

    def write_bytes(self, path: str, content: bytes) -> None:
        self.bytes_files[path] = content

    def read_text(self, path: str) -> str:
        return self.text_files[path]

    def read_bytes(self, path: str) -> bytes:
        return self.bytes_files[path]

    def list_files(self, path: str = ".") -> list[str]:
        return ["data.bin", "game.py"]

    def mkdir(self, path: str, *, parents: bool = True) -> None:
        self.mkdir_calls.append((path, parents))

    def remove(self, path: str, *, recursive: bool = False) -> None:
        self.remove_calls.append((path, recursive))

    def copy_from_local(self, local_path: str | os.PathLike[str], remote_path: str) -> None:
        self.copy_from_local_calls.append((str(local_path), remote_path))

    def copy_to_local(self, remote_path: str, local_path: str | os.PathLike[str]) -> None:
        self.copy_to_local_calls.append((remote_path, str(local_path)))

    def close(self) -> None:
        self.closed = True

    def detach(self) -> None:
        self.detached = True

    def terminate(self, *, wait: bool = True) -> None:
        self.terminated = wait

    def domain(self, port: int) -> str:
        self.domain_calls.append(port)
        return f"https://sandbox.example/{port}"

    def create_snapshot(self) -> SandboxSnapshot:
        self.snapshot_created = True
        return SandboxSnapshot(name="workspace-snapshot", kind="modal_volume", workspace=self.config.workspace)


class FakeStream:
    def __init__(self, chunks: list[str]):
        self._chunks = chunks

    def __iter__(self):
        return iter(self._chunks)


class FakeDetachedProcess:
    def __init__(self) -> None:
        self.stdout = FakeStream(["one\n", "two\n"])
        self.stderr = FakeStream(["err\n"])
        self.returncode: int | None = None

    def wait(self) -> int:
        self.returncode = 0
        return 0

    def poll(self) -> int | None:
        return self.returncode


def test_run_returns_command_result() -> None:
    sandbox = Sandbox.from_provider(FakeProvider())

    result = sandbox.run("python -c 'print(123)'")

    assert result.stdout == "123\n"
    assert result.stderr == ""
    assert result.exit_code == 0
    assert result.timed_out is False


def test_nonzero_exit_code_is_returned_not_raised() -> None:
    sandbox = Sandbox.from_provider(FakeProvider())

    result = sandbox.run("sh -c 'exit 7'")

    assert result.exit_code == 7


def test_timeout_is_represented_in_command_result() -> None:
    sandbox = Sandbox.from_provider(FakeProvider())

    result = sandbox.run("sleep 10")

    assert result.timed_out is True
    assert result.exit_code is None


def test_run_passes_timeout_and_cwd_to_provider() -> None:
    provider = FakeProvider()
    sandbox = Sandbox.from_provider(provider)

    sandbox.run("pwd", timeout=9, cwd="/tmp")

    assert provider.commands[-1] == ("pwd", 9, "/tmp")


def test_run_passes_max_output_bytes_to_provider() -> None:
    provider = FakeProvider()
    sandbox = Sandbox.from_provider(provider)

    result = sandbox.run("pwd", max_output_bytes=123)

    assert result.max_output_bytes == 123


def test_run_command_uses_argv_style_provider_api() -> None:
    provider = FakeProvider()
    sandbox = Sandbox.from_provider(provider)

    result = sandbox.run_command("python", ["-c", "print(123)"], cwd="/work", env={"A": "B"}, timeout=8)

    assert result.stdout == "argv ok\n"
    assert result.command == "python -c 'print(123)'"
    assert provider.argv_commands == [("python", ("-c", "print(123)"), "/work", {"A": "B"}, 8)]


def test_run_command_detached_returns_command_handle() -> None:
    sandbox = Sandbox.from_provider(FakeProvider())

    command = sandbox.run_command_detached("npm", ["run", "dev"])

    assert list(command.logs()) == ["one\n", "two\n"]
    assert list(command.logs("stderr")) == ["err\n"]
    assert command.poll() is None
    assert command.wait() == 0
    assert command.returncode == 0


def test_sandbox_command_rejects_unknown_log_stream() -> None:
    command = SandboxCommand(FakeDetachedProcess())

    with pytest.raises(ValueError, match="stream"):
        list(command.logs("stdin"))


def test_create_accepts_unlimited_max_output_bytes(monkeypatch) -> None:
    created_configs: list[SandboxConfig] = []

    class CapturingProvider(FakeProvider):
        @classmethod
        def create(cls, config: SandboxConfig) -> CapturingProvider:
            created_configs.append(config)
            provider = cls()
            provider.config = config
            return provider

    monkeypatch.setattr("sandbox.sandbox.ModalSandboxProvider", CapturingProvider)

    sandbox = Sandbox.create(max_output_bytes=None)

    assert sandbox.config.max_output_bytes is None
    assert created_configs[-1].max_output_bytes is None


def test_create_resolves_runtime_alias(monkeypatch) -> None:
    created_configs: list[SandboxConfig] = []

    class CapturingProvider(FakeProvider):
        @classmethod
        def create(cls, config: SandboxConfig) -> CapturingProvider:
            created_configs.append(config)
            provider = cls()
            provider.config = config
            return provider

    monkeypatch.setattr("sandbox.sandbox.ModalSandboxProvider", CapturingProvider)

    Sandbox.create(runtime="node24")

    assert created_configs[-1].runtime == "node24"
    assert created_configs[-1].image == "node:24-slim"


def test_create_stores_name_and_tags(monkeypatch) -> None:
    created_configs: list[SandboxConfig] = []

    class CapturingProvider(FakeProvider):
        @classmethod
        def create(cls, config: SandboxConfig) -> CapturingProvider:
            created_configs.append(config)
            provider = cls()
            provider.config = config
            return provider

    monkeypatch.setattr("sandbox.sandbox.ModalSandboxProvider", CapturingProvider)

    Sandbox.create(name=" agent.workspace_1 ", tags={" kind ": "frontend", "owner": "team"})

    assert created_configs[-1].name == "agent.workspace_1"
    assert created_configs[-1].tags == {"kind": "frontend", "owner": "team"}


def test_create_rejects_invalid_name_and_tags() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        Sandbox.create(name="")

    with pytest.raises(ValueError, match="letters, numbers"):
        Sandbox.create(name="bad name")

    with pytest.raises(ValueError, match="shorter than 64"):
        Sandbox.create(name="a" * 64)

    with pytest.raises(TypeError, match="tag keys"):
        Sandbox.create(tags={1: "value"})  # type: ignore[dict-item]

    with pytest.raises(TypeError, match="tag values"):
        Sandbox.create(tags={"key": 123})  # type: ignore[dict-item]

    with pytest.raises(ValueError, match="tag keys"):
        Sandbox.create(tags={" ": "value"})


def test_from_name_attaches_to_provider(monkeypatch) -> None:
    from_name_calls: list[tuple[str, SandboxConfig, bool]] = []

    class CapturingProvider(FakeProvider):
        @classmethod
        def from_name(cls, name: str, config: SandboxConfig, *, ensure_workspace: bool = True) -> CapturingProvider:
            from_name_calls.append((name, config, ensure_workspace))
            provider = cls()
            provider.config = config
            return provider

    monkeypatch.setattr("sandbox.sandbox.ModalSandboxProvider", CapturingProvider)

    sandbox = Sandbox.from_name("agent-workspace", command_timeout=45, ensure_workspace=False)

    assert sandbox.config.name == "agent-workspace"
    assert from_name_calls == [("agent-workspace", sandbox.config, False)]


def test_get_or_create_returns_existing_named_sandbox(monkeypatch) -> None:
    callbacks: list[Sandbox] = []
    from_name_calls: list[str] = []
    create_calls: list[SandboxConfig] = []

    class CapturingProvider(FakeProvider):
        @classmethod
        def from_name(cls, name: str, config: SandboxConfig, *, ensure_workspace: bool = True) -> CapturingProvider:
            from_name_calls.append(name)
            provider = cls()
            provider.config = config
            return provider

        @classmethod
        def create(cls, config: SandboxConfig) -> CapturingProvider:
            create_calls.append(config)
            provider = cls()
            provider.config = config
            return provider

    monkeypatch.setattr("sandbox.sandbox.ModalSandboxProvider", CapturingProvider)

    sandbox = Sandbox.get_or_create("agent-workspace", on_create=callbacks.append, tags={"kind": "existing"})

    assert sandbox.config.name == "agent-workspace"
    assert from_name_calls == ["agent-workspace"]
    assert create_calls == []
    assert callbacks == []


def test_get_or_create_creates_only_on_not_found(monkeypatch) -> None:
    callbacks: list[Sandbox] = []
    create_calls: list[SandboxConfig] = []

    class MissingProvider(FakeProvider):
        @classmethod
        def from_name(cls, name: str, config: SandboxConfig, *, ensure_workspace: bool = True) -> MissingProvider:
            raise SandboxNotFoundError("missing")

        @classmethod
        def create(cls, config: SandboxConfig) -> MissingProvider:
            create_calls.append(config)
            provider = cls()
            provider.config = config
            return provider

    monkeypatch.setattr("sandbox.sandbox.ModalSandboxProvider", MissingProvider)

    sandbox = Sandbox.get_or_create(
        "agent-workspace",
        runtime="python3.13",
        tags={"kind": "created"},
        on_create=callbacks.append,
    )

    assert sandbox.config.name == "agent-workspace"
    assert sandbox.config.image == "python:3.13-slim"
    assert sandbox.config.tags == {"kind": "created"}
    assert create_calls == [sandbox.config]
    assert callbacks == [sandbox]


def test_get_or_create_does_not_swallow_provider_errors(monkeypatch) -> None:
    class BrokenProvider(FakeProvider):
        @classmethod
        def from_name(cls, name: str, config: SandboxConfig, *, ensure_workspace: bool = True) -> BrokenProvider:
            raise SandboxProviderError("permission denied")

    monkeypatch.setattr("sandbox.sandbox.ModalSandboxProvider", BrokenProvider)

    with pytest.raises(SandboxProviderError, match="permission denied"):
        Sandbox.get_or_create("agent-workspace")


def test_create_stores_declared_ports(monkeypatch) -> None:
    created_configs: list[SandboxConfig] = []

    class CapturingProvider(FakeProvider):
        @classmethod
        def create(cls, config: SandboxConfig) -> CapturingProvider:
            created_configs.append(config)
            provider = cls()
            provider.config = config
            return provider

    monkeypatch.setattr("sandbox.sandbox.ModalSandboxProvider", CapturingProvider)

    Sandbox.create(encrypted_ports=[3000], unencrypted_ports=[9229])

    assert created_configs[-1].encrypted_ports == (3000,)
    assert created_configs[-1].unencrypted_ports == (9229,)


def test_create_stores_outbound_domain_allowlist(monkeypatch) -> None:
    created_configs: list[SandboxConfig] = []

    class CapturingProvider(FakeProvider):
        @classmethod
        def create(cls, config: SandboxConfig) -> CapturingProvider:
            created_configs.append(config)
            provider = cls()
            provider.config = config
            return provider

    monkeypatch.setattr("sandbox.sandbox.ModalSandboxProvider", CapturingProvider)

    Sandbox.create(outbound_domain_allowlist=[" api.openai.com ", "github.com"])

    assert created_configs[-1].outbound_domain_allowlist == ("api.openai.com", "github.com")


def test_create_stores_cidr_allowlists(monkeypatch) -> None:
    created_configs: list[SandboxConfig] = []

    class CapturingProvider(FakeProvider):
        @classmethod
        def create(cls, config: SandboxConfig) -> CapturingProvider:
            created_configs.append(config)
            provider = cls()
            provider.config = config
            return provider

    monkeypatch.setattr("sandbox.sandbox.ModalSandboxProvider", CapturingProvider)

    Sandbox.create(
        outbound_cidr_allowlist=[" 10.0.1.5/24 ", "2001:db8::/32"],
        inbound_cidr_allowlist=["203.0.113.0/24"],
    )

    assert created_configs[-1].outbound_cidr_allowlist == ("10.0.1.5/24", "2001:db8::/32")
    assert created_configs[-1].inbound_cidr_allowlist == ("203.0.113.0/24",)


def test_create_accepts_first_class_volume_mounts(monkeypatch) -> None:
    created_configs: list[SandboxConfig] = []

    class CapturingProvider(FakeProvider):
        @classmethod
        def create(cls, config: SandboxConfig) -> CapturingProvider:
            created_configs.append(config)
            provider = cls()
            provider.config = config
            return provider

    monkeypatch.setattr("sandbox.sandbox.ModalSandboxProvider", CapturingProvider)

    Sandbox.create(
        volumes=[
            SandboxVolume(volume="cache-volume", mount_path="/cache", create_if_missing=False),
            SandboxVolume(volume="data-volume", mount_path="/data"),
        ]
    )

    assert created_configs[-1].volumes == (
        SandboxVolume(volume="cache-volume", mount_path="/cache", create_if_missing=False),
        SandboxVolume(volume="data-volume", mount_path="/data", create_if_missing=True),
    )


def test_create_rejects_invalid_volume_mounts() -> None:
    with pytest.raises(ValueError, match="absolute sandbox path"):
        Sandbox.create(volumes=[SandboxVolume(volume="cache-volume", mount_path="cache")])

    with pytest.raises(ValueError, match="Duplicate"):
        Sandbox.create(
            volumes=[
                SandboxVolume.workspace("workspace-volume"),
                SandboxVolume.workspace("other-volume"),
            ]
        )


def test_create_rejects_invalid_domain_allowlist() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        Sandbox.create(outbound_domain_allowlist=[""])

    with pytest.raises(TypeError, match="must contain strings"):
        Sandbox.create(outbound_domain_allowlist=["api.openai.com", 123])  # type: ignore[list-item]

    with pytest.raises(ValueError, match="hostnames"):
        Sandbox.create(outbound_domain_allowlist=["https://api.openai.com"])

    with pytest.raises(ValueError, match="hostnames"):
        Sandbox.create(outbound_domain_allowlist=["api.openai.com/path"])

    with pytest.raises(ValueError, match="domain names"):
        Sandbox.create(outbound_domain_allowlist=["127.0.0.1"])


def test_create_rejects_invalid_cidr_allowlists() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        Sandbox.create(outbound_cidr_allowlist=[""])

    with pytest.raises(TypeError, match="must contain strings"):
        Sandbox.create(outbound_cidr_allowlist=["10.0.0.0/8", 123])  # type: ignore[list-item]

    with pytest.raises(ValueError, match="CIDR ranges"):
        Sandbox.create(outbound_cidr_allowlist=["10.0.0.1"])

    with pytest.raises(ValueError, match="valid CIDR ranges"):
        Sandbox.create(inbound_cidr_allowlist=["not-a-cidr/24"])


def test_create_rejects_block_network_with_allowlists() -> None:
    with pytest.raises(ValueError, match="block_network cannot be combined"):
        Sandbox.create(block_network=True, outbound_domain_allowlist=["api.openai.com"])

    with pytest.raises(ValueError, match="block_network cannot be combined"):
        Sandbox.create(block_network=True, outbound_cidr_allowlist=["10.0.0.0/8"])

    with pytest.raises(ValueError, match="block_network cannot be combined"):
        Sandbox.create(block_network=True, inbound_cidr_allowlist=["203.0.113.0/24"])


def test_create_rejects_runtime_and_image_conflict() -> None:
    with pytest.raises(ValueError, match="either runtime or image"):
        Sandbox.create(runtime="python3.13", image="python:3.13-slim")


def test_from_snapshot_uses_snapshot_name_as_workspace_volume(monkeypatch) -> None:
    created_configs: list[SandboxConfig] = []

    class CapturingProvider(FakeProvider):
        @classmethod
        def create(cls, config: SandboxConfig) -> CapturingProvider:
            created_configs.append(config)
            provider = cls()
            provider.config = config
            return provider

    monkeypatch.setattr("sandbox.sandbox.ModalSandboxProvider", CapturingProvider)

    sandbox = Sandbox.from_snapshot("snapshot-volume", runtime="python3.13")

    assert sandbox.config.volumes == (SandboxVolume.workspace("snapshot-volume"),)
    assert created_configs[-1].volumes == (SandboxVolume.workspace("snapshot-volume"),)
    assert created_configs[-1].image == "python:3.13-slim"


def test_file_helpers_delegate_to_provider() -> None:
    provider = FakeProvider()
    sandbox = Sandbox.from_provider(provider)

    sandbox.write_text("game.py", "print('hello')")
    sandbox.write_bytes("data.bin", b"updated")
    sandbox.mkdir("notes", parents=True)
    sandbox.remove("notes", recursive=True)
    sandbox.copy_from_local("local.txt", "remote.txt")
    sandbox.copy_to_local("remote.txt", "local.txt")

    assert sandbox.read_text("game.py") == "print('hello')"
    assert sandbox.read_bytes("data.bin") == b"updated"
    assert sandbox.list_files(".") == ["data.bin", "game.py"]
    assert provider.mkdir_calls == [("notes", True)]
    assert provider.remove_calls == [("notes", True)]
    assert provider.copy_from_local_calls == [("local.txt", "remote.txt")]
    assert provider.copy_to_local_calls == [("remote.txt", "local.txt")]


def test_write_files_accepts_dataclasses_and_mappings() -> None:
    provider = FakeProvider()
    sandbox = Sandbox.from_provider(provider)

    sandbox.write_files(
        [
            SandboxFile(path="hello.py", content="print('hello')"),
            {"path": "data.bin", "content": b"data"},
        ]
    )

    assert provider.text_files["hello.py"] == "print('hello')"
    assert provider.bytes_files["data.bin"] == b"data"


def test_write_files_applies_modes_with_argv_chmod() -> None:
    provider = FakeProvider()
    sandbox = Sandbox.from_provider(provider)

    sandbox.write_files(
        [
            SandboxFile(path="script.sh", content="#!/bin/sh\necho ok\n", mode=0o755),
            {"path": "private.txt", "content": "secret\n", "mode": 0o600},
        ]
    )

    assert provider.text_files["script.sh"] == "#!/bin/sh\necho ok\n"
    assert provider.text_files["private.txt"] == "secret\n"
    assert provider.argv_commands[-2:] == [
        ("chmod", ("755", "/workspace/script.sh"), None, None, None),
        ("chmod", ("600", "/workspace/private.txt"), None, None, None),
    ]


def test_write_files_rejects_invalid_modes() -> None:
    sandbox = Sandbox.from_provider(FakeProvider())

    with pytest.raises(TypeError, match="mode"):
        sandbox.write_files([{"path": "script.sh", "content": "echo ok\n", "mode": "755"}])

    with pytest.raises(ValueError, match="between"):
        sandbox.write_files([SandboxFile(path="script.sh", content="echo ok\n", mode=0o10000)])


def test_write_files_raises_when_chmod_fails() -> None:
    class FailingChmodProvider(FakeProvider):
        def run_command(
            self,
            cmd: str,
            args: Sequence[str] | None = None,
            *,
            cwd: str | None = None,
            env: Mapping[str, str | None] | None = None,
            timeout: int | None = None,
            max_output_bytes: int | None = None,
        ) -> CommandResult:
            return CommandResult("chmod", "", "permission denied", 1, 1, max_output_bytes=max_output_bytes)

    sandbox = Sandbox.from_provider(FailingChmodProvider())

    with pytest.raises(SandboxProviderError, match="chmod failed"):
        sandbox.write_files([SandboxFile(path="script.sh", content="echo ok\n", mode=0o755)])


def test_write_files_rejects_invalid_mappings() -> None:
    sandbox = Sandbox.from_provider(FakeProvider())

    with pytest.raises(TypeError, match="path"):
        sandbox.write_files([{"content": "missing path"}])


def test_context_manager_closes_provider() -> None:
    provider = FakeProvider()

    with Sandbox.from_provider(provider) as sandbox:
        assert sandbox.config == provider.config

    assert provider.closed is True


def test_lifecycle_helpers_delegate_to_provider() -> None:
    provider = FakeProvider()
    sandbox = Sandbox.from_provider(provider)

    sandbox.detach()
    sandbox.terminate(wait=True)

    assert sandbox.sandbox_id == "sb-fake"
    assert provider.detached is True
    assert provider.terminated is True


def test_domain_and_snapshot_delegate_to_provider() -> None:
    provider = FakeProvider()
    sandbox = Sandbox.from_provider(provider)

    snapshot = sandbox.create_snapshot()

    assert sandbox.domain(3000) == "https://sandbox.example/3000"
    assert provider.domain_calls == [3000]
    assert snapshot == SandboxSnapshot(name="workspace-snapshot", kind="modal_volume", workspace="/workspace")
    assert provider.snapshot_created is True


def test_public_exception_hierarchy() -> None:
    assert issubclass(SandboxProviderError, SandboxError)
    assert issubclass(SandboxConfigurationError, SandboxError)
    assert issubclass(SandboxConfigurationError, ValueError)
