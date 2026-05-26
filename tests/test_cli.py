from __future__ import annotations

import json

from sandbox import CommandResult
from sandbox_cli import cli


class FakeSandbox:
    create_calls: list[dict[str, object]] = []

    @classmethod
    def create(cls, **kwargs: object) -> "FakeSandbox":
        cls.create_calls.append(kwargs)
        return cls()

    def run(self, command: str) -> CommandResult:
        return CommandResult(command, "ok\n", "", 0, 1)

    def write_text(self, path: str, content: str) -> None:
        self.written = (path, content)

    def read_text(self, path: str) -> str:
        return "file contents"

    def list_files(self, path: str = ".") -> list[str]:
        return ["game.py"]

    def close(self) -> None:
        self.closed = True


def test_cli_run_outputs_json(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(
        [
            "--image",
            "python:3.13-slim",
            "--workspace-volume",
            "workspace-volume",
            "--env",
            "A=B",
            "--timeout",
            "12",
            "--sandbox-timeout",
            "99",
            "--cpu",
            "2",
            "--memory",
            "512",
            "--gpu",
            "T4",
            "--region",
            "us-east-1",
            "--block-network",
            "run",
            "python -c 'print(123)'",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "python -c 'print(123)'"
    assert payload["stdout"] == "ok\n"
    assert FakeSandbox.create_calls == [
        {
            "app_name": "modal-sandbox-sdk",
            "workspace": "/workspace",
            "image": "python:3.13-slim",
            "workspace_volume": "workspace-volume",
            "env": {"A": "B"},
            "command_timeout": 12,
            "sandbox_timeout": 99,
            "cpu": 2.0,
            "memory": 512,
            "gpu": "T4",
            "region": "us-east-1",
            "block_network": True,
            "sandbox_id": None,
        }
    ]


def test_cli_write_read_and_ls(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    assert cli.main(["write", "game.py", "--content", "print('hello')"]) == 0
    write_payload = json.loads(capsys.readouterr().out)
    assert write_payload == {"path": "game.py", "status": "wrote"}

    assert cli.main(["read", "game.py"]) == 0
    read_payload = json.loads(capsys.readouterr().out)
    assert read_payload == {"content": "file contents", "path": "game.py"}

    assert cli.main(["ls", "."]) == 0
    ls_payload = json.loads(capsys.readouterr().out)
    assert ls_payload == {"files": ["game.py"], "path": "."}
