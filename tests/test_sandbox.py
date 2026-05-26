from __future__ import annotations

from sandbox import CommandResult, Sandbox, SandboxConfig


class FakeProvider:
    def __init__(self) -> None:
        self.config = SandboxConfig()
        self.commands: list[tuple[str, int | None, str | None]] = []
        self.text_files = {"game.py": "print('hello')"}
        self.bytes_files = {"data.bin": b"hello"}
        self.mkdir_calls: list[tuple[str, bool]] = []
        self.remove_calls: list[tuple[str, bool]] = []
        self.copy_from_local_calls: list[tuple[str, str]] = []
        self.copy_to_local_calls: list[tuple[str, str]] = []
        self.closed = False

    def run(self, command: str, timeout: int | None = None, cwd: str | None = None) -> CommandResult:
        self.commands.append((command, timeout, cwd))
        if command == "python -c 'print(123)'":
            return CommandResult(command, "123\n", "", 0, 5)
        if command == "sh -c 'exit 7'":
            return CommandResult(command, "", "", 7, 4)
        if command == "sleep 10":
            return CommandResult(command, "", "timed out", None, 1000, timed_out=True)
        return CommandResult(command, "", "", 0, 1)

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

    def copy_from_local(self, local_path: str, remote_path: str) -> None:
        self.copy_from_local_calls.append((local_path, remote_path))

    def copy_to_local(self, remote_path: str, local_path: str) -> None:
        self.copy_to_local_calls.append((remote_path, local_path))

    def close(self) -> None:
        self.closed = True


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
    assert sandbox.read_file("game.py") == "print('hello')"
    assert sandbox.read_bytes("data.bin") == b"updated"
    assert sandbox.list_files(".") == ["data.bin", "game.py"]
    assert provider.mkdir_calls == [("notes", True)]
    assert provider.remove_calls == [("notes", True)]
    assert provider.copy_from_local_calls == [("local.txt", "remote.txt")]
    assert provider.copy_to_local_calls == [("remote.txt", "local.txt")]


def test_context_manager_closes_provider() -> None:
    provider = FakeProvider()

    with Sandbox.from_provider(provider) as sandbox:
        assert sandbox.config == provider.config

    assert provider.closed is True
