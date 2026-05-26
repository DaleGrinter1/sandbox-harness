from __future__ import annotations

import json

import pytest

from sandbox import CommandResult, ModalAuthenticationError
from sandbox_cli import cli


class FakeSandbox:
    create_calls: list[dict[str, object]] = []
    instances: list["FakeSandbox"] = []
    raise_auth_error = False

    @classmethod
    def create(cls, **kwargs: object) -> "FakeSandbox":
        if cls.raise_auth_error:
            raise ModalAuthenticationError("Run modal setup before using Modal sandboxes.")
        sandbox = cls()
        cls.create_calls.append(kwargs)
        cls.instances.append(sandbox)
        return sandbox

    def __init__(self) -> None:
        self.run_calls: list[tuple[str, str | None]] = []
        self.mkdir_calls: list[tuple[str, bool]] = []
        self.remove_calls: list[tuple[str, bool]] = []
        self.copy_from_local_calls: list[tuple[str, str]] = []
        self.copy_to_local_calls: list[tuple[str, str]] = []

    def run(self, command: str, cwd: str | None = None) -> CommandResult:
        self.run_calls.append((command, cwd))
        if command == "sh -c 'exit 7'":
            return CommandResult(command, "", "", 7, 1)
        return CommandResult(command, "ok\n", "", 0, 1)

    def write_text(self, path: str, content: str) -> None:
        self.written = (path, content)

    def read_text(self, path: str) -> str:
        return "file contents"

    def list_files(self, path: str = ".") -> list[str]:
        return ["game.py"]

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


def test_cli_run_outputs_json(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
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
    assert FakeSandbox.instances[-1].run_calls == [("python -c 'print(123)'", None)]
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
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
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


def test_cli_run_can_pass_cwd_and_return_command_exit_code(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(["run", "--cwd", "/tmp", "--use-command-exit-code", "sh -c 'exit 7'"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 7
    assert payload["exit_code"] == 7
    assert FakeSandbox.instances[-1].run_calls == [("sh -c 'exit 7'", "/tmp")]


def test_cli_mkdir_rm_upload_and_download(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    assert cli.main(["mkdir", "notes", "--no-parents"]) == 0
    mkdir_payload = json.loads(capsys.readouterr().out)
    assert mkdir_payload == {"parents": False, "path": "notes", "status": "created"}
    assert FakeSandbox.instances[-1].mkdir_calls == [("notes", False)]

    assert cli.main(["rm", "notes", "--recursive"]) == 0
    rm_payload = json.loads(capsys.readouterr().out)
    assert rm_payload == {"path": "notes", "recursive": True, "status": "removed"}
    assert FakeSandbox.instances[-1].remove_calls == [("notes", True)]

    assert cli.main(["upload", "input.txt", "remote/input.txt"]) == 0
    upload_payload = json.loads(capsys.readouterr().out)
    assert upload_payload == {
        "local_path": "input.txt",
        "remote_path": "remote/input.txt",
        "status": "uploaded",
    }
    assert FakeSandbox.instances[-1].copy_from_local_calls == [("input.txt", "remote/input.txt")]

    assert cli.main(["download", "remote/output.txt", "output.txt"]) == 0
    download_payload = json.loads(capsys.readouterr().out)
    assert download_payload == {
        "local_path": "output.txt",
        "remote_path": "remote/output.txt",
        "status": "downloaded",
    }
    assert FakeSandbox.instances[-1].copy_to_local_calls == [("remote/output.txt", "output.txt")]


def test_cli_invalid_env_reports_error_without_traceback(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    with pytest.raises(SystemExit) as exc:
        cli.main(["--env", "INVALID", "run", "true"])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert captured.out == ""
    assert "sandbox: error: --env values must use KEY=VALUE" in captured.err


def test_cli_modal_auth_error_reports_setup_guidance_without_traceback(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = True
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    with pytest.raises(SystemExit) as exc:
        cli.main(["run", "true"])

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert captured.out == ""
    assert "sandbox: error: Run modal setup before using Modal sandboxes." in captured.err


def test_cli_schema_outputs_agent_readable_metadata_without_creating_sandbox(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = True
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)
    monkeypatch.setattr(cli, "_package_version", lambda: "0.1.0")

    exit_code = cli.main(["schema"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["name"] == "sandbox"
    assert payload["default_output"] == "json"
    assert payload["commands"]["run"]["output"]["stdout"] == "string"
    assert payload["commands"]["schema"]["creates_sandbox"] is False
    assert payload["commands"]["doctor"]["creates_sandbox"] is False
    assert payload["auth"]["setup_commands"][0] == "modal setup"
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.instances == []


def test_cli_doctor_reports_modal_readiness_without_creating_sandbox(monkeypatch, capsys, tmp_path) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = True
    config_path = tmp_path / ".modal.toml"
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)
    monkeypatch.setattr(cli, "_modal_package_info", lambda: {"installed": True, "version": "1.4.3"})
    monkeypatch.setattr(cli, "_modal_config_path", lambda: config_path)
    monkeypatch.delenv("MODAL_TOKEN_ID", raising=False)
    monkeypatch.delenv("MODAL_TOKEN_SECRET", raising=False)

    exit_code = cli.main(["doctor"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["modal_package"] == {"installed": True, "version": "1.4.3"}
    assert payload["credentials"]["status"] == "missing_or_unknown"
    assert payload["credentials"]["modal_toml"]["path"] == str(config_path)
    assert payload["creates_modal_resources"] is False
    assert payload["setup_commands"][0] == "modal setup"
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.instances == []
