from __future__ import annotations

import json

from modal_agent_sandbox import CommandResult
from modal_agent_sandbox import cli


class FakeSandbox:
    closed = False

    @classmethod
    def create(cls, **kwargs: object) -> "FakeSandbox":
        return cls()

    def run(self, command: str) -> CommandResult:
        return CommandResult(command, "ok\n", "", 0, 1)

    def write_file(self, path: str, content: str) -> CommandResult:
        return CommandResult(f"write {path}", "", "", 0, 1)

    def read_file(self, path: str) -> str:
        return "file contents"

    def list_files(self, path: str = ".") -> list[str]:
        return ["game.py"]

    def close(self) -> None:
        self.closed = True


def test_cli_run_outputs_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(["run", "python -c 'print(123)'"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "python -c 'print(123)'"
    assert payload["stdout"] == "ok\n"


def test_cli_write_read_and_ls(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    assert cli.main(["write", "game.py", "--content", "print('hello')"]) == 0
    write_payload = json.loads(capsys.readouterr().out)
    assert write_payload["exit_code"] == 0

    assert cli.main(["read", "game.py"]) == 0
    read_payload = json.loads(capsys.readouterr().out)
    assert read_payload == {"content": "file contents", "path": "game.py"}

    assert cli.main(["ls", "."]) == 0
    ls_payload = json.loads(capsys.readouterr().out)
    assert ls_payload == {"files": ["game.py"], "path": "."}
