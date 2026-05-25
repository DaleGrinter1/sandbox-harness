from __future__ import annotations

from modal_agent_sandbox import CommandResult, Sandbox, SandboxConfig


class FakeProvider:
    def __init__(self) -> None:
        self.config = SandboxConfig(use_volume=False)
        self.commands: list[tuple[str, str | None]] = []
        self.files = {"game.py": "print('hello')"}

    def run(self, command: str, timeout: int | None = None, cwd: str | None = None) -> CommandResult:
        self.commands.append((command, cwd))
        if command == "python -c 'print(123)'":
            return CommandResult(command, "123\n", "", 0, 5)
        if command == "sh -c 'exit 7'":
            return CommandResult(command, "", "", 7, 4)
        if command.startswith("cat /workspace/game.py"):
            return CommandResult(command, self.files["game.py"], "", 0, 3)
        if command.startswith("find /workspace"):
            return CommandResult(command, "game.py\n", "", 0, 3)
        if "write_bytes" in command:
            return CommandResult(command, "", "", 0, 3)
        if command == "sleep 10":
            return CommandResult(command, "", "timed out", None, 1000, timed_out=True)
        return CommandResult(command, "", "", 0, 1)

    def close(self) -> None:
        self.commands.append(("close", None))


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


def test_file_helpers_use_sandbox_side_commands() -> None:
    provider = FakeProvider()
    sandbox = Sandbox.from_provider(provider)

    write_result = sandbox.write_file("game.py", "print('hello')")
    content = sandbox.read_file("game.py")
    files = sandbox.list_files(".")

    assert write_result.exit_code == 0
    assert content == "print('hello')"
    assert files == ["game.py"]
    assert any("write_bytes" in command for command, _ in provider.commands)
    assert ("cat /workspace/game.py", "/") in provider.commands
    assert any(command.startswith("find /workspace") for command, _ in provider.commands)
