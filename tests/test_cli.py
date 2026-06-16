from __future__ import annotations

import json
import sys
from typing import cast

import pytest
from sandbox import CommandResult, ModalAuthenticationError, SandboxConfig, SandboxSnapshot, SandboxVolume
from sandbox_cli import cli


class FakeSandbox:
    create_calls: list[dict[str, object]] = []
    from_id_calls: list[dict[str, object]] = []
    instances: list[FakeSandbox] = []
    raise_auth_error = False

    @classmethod
    def create(cls, **kwargs: object) -> FakeSandbox:
        if cls.raise_auth_error:
            raise ModalAuthenticationError("Run modal setup before using Modal sandboxes.")
        sandbox = cls()
        sandbox_timeout = kwargs.get("sandbox_timeout", 300)
        max_output_bytes = kwargs.get("max_output_bytes")
        volumes = kwargs.get("volumes", ())
        if not isinstance(volumes, tuple):
            volumes = ()
        volumes = cast(tuple[SandboxVolume, ...], volumes)
        sandbox.config = SandboxConfig(
            workspace=str(kwargs.get("workspace", "/workspace")),
            sandbox_timeout=sandbox_timeout if isinstance(sandbox_timeout, int) else 300,
            max_output_bytes=max_output_bytes if isinstance(max_output_bytes, int) else None,
            volumes=volumes,
        )
        cls.create_calls.append(kwargs)
        cls.instances.append(sandbox)
        return sandbox

    @classmethod
    def from_id(cls, sandbox_id: str, **kwargs: object) -> FakeSandbox:
        sandbox = cls(sandbox_id=sandbox_id)
        cls.from_id_calls.append({"sandbox_id": sandbox_id, **kwargs})
        cls.instances.append(sandbox)
        return sandbox

    def __init__(self, sandbox_id: str = "sb-fake") -> None:
        self.sandbox_id = sandbox_id
        self.config = SandboxConfig()
        self.run_calls: list[tuple[str, str | None]] = []
        self.run_command_calls: list[tuple[str, list[str], str | None, dict[str, str] | None]] = []
        self.mkdir_calls: list[tuple[str, bool]] = []
        self.remove_calls: list[tuple[str, bool]] = []
        self.copy_from_local_calls: list[tuple[str, str]] = []
        self.copy_to_local_calls: list[tuple[str, str]] = []
        self.detached = False
        self.terminated = False

    def run(self, command: str, cwd: str | None = None, max_output_bytes: int | None = None) -> CommandResult:
        self.run_calls.append((command, cwd))
        if command == "sh -c 'exit 7'":
            return CommandResult(command, "", "", 7, 1, max_output_bytes=max_output_bytes)
        return CommandResult(command, "ok\n", "", 0, 1, max_output_bytes=max_output_bytes)

    def run_command(
        self,
        cmd: str,
        args: list[str] | None = None,
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        max_output_bytes: int | None = None,
    ) -> CommandResult:
        self.run_command_calls.append((cmd, args or [], cwd, env))
        return CommandResult("python -c 'print(123)'", "argv ok\n", "", 0, 1, max_output_bytes=max_output_bytes)

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

    def detach(self) -> None:
        self.detached = True

    def terminate(self, *, wait: bool = True) -> None:
        self.terminated = wait

    def domain(self, port: int) -> str:
        return f"https://sandbox.example/{port}"

    def create_snapshot(self) -> SandboxSnapshot:
        workspace = self.config.workspace.rstrip("/") or "/"
        for volume in self.config.volumes:
            mount_path = volume.mount_path.rstrip("/") or "/"
            if mount_path == workspace and isinstance(volume.volume, str):
                return SandboxSnapshot(name=volume.volume, kind="modal_volume", workspace=self.config.workspace)
        raise ValueError("create_snapshot requires a string workspace volume.")


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
            "runtime": None,
            "volumes": (SandboxVolume.workspace("workspace-volume"),),
            "env": {"A": "B"},
            "command_timeout": 12,
            "sandbox_timeout": 99,
            "cpu": 2.0,
            "memory": 512,
            "gpu": "T4",
            "region": "us-east-1",
            "block_network": True,
            "max_output_bytes": 10 * 1024 * 1024,
            "encrypted_ports": (),
            "unencrypted_ports": (),
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


def test_cli_write_accepts_content_file(monkeypatch, capsys, tmp_path) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    content_file = tmp_path / "input.py"
    content_file.write_text("print('from file')\n", encoding="utf-8")
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    assert cli.main(["write", "game.py", "--content-file", str(content_file)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload == {"path": "game.py", "status": "wrote"}
    assert FakeSandbox.instances[-1].written == ("game.py", "print('from file')\n")


def test_cli_write_accepts_stdin(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)
    monkeypatch.setattr(sys, "stdin", type("FakeStdin", (), {"read": lambda self: "print('stdin')\n"})())

    assert cli.main(["write", "game.py", "--stdin"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload == {"path": "game.py", "status": "wrote"}
    assert FakeSandbox.instances[-1].written == ("game.py", "print('stdin')\n")


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


def test_cli_run_passes_max_output_bytes(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(["--max-output-bytes", "2048", "run", "echo ok"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["max_output_bytes"] == 2048
    assert FakeSandbox.create_calls[-1]["max_output_bytes"] == 2048


def test_cli_create_accepts_runtime_and_declared_ports(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(
        [
            "--runtime",
            "node24",
            "--encrypted-port",
            "3000",
            "--unencrypted-port",
            "9229",
            "--volume",
            "cache-volume:/cache",
            "run",
            "node --version",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["stdout"] == "ok\n"
    assert FakeSandbox.create_calls[-1]["image"] is None
    assert FakeSandbox.create_calls[-1]["runtime"] == "node24"
    assert FakeSandbox.create_calls[-1]["volumes"] == (SandboxVolume(volume="cache-volume", mount_path="/cache"),)
    assert FakeSandbox.create_calls[-1]["encrypted_ports"] == (3000,)
    assert FakeSandbox.create_calls[-1]["unencrypted_ports"] == (9229,)


def test_cli_create_accepts_outbound_domain_allowlist(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(
        [
            "--allow-domain",
            "api.openai.com",
            "--allow-domain",
            "github.com",
            "run",
            "python -c 'print(123)'",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["stdout"] == "ok\n"
    assert FakeSandbox.create_calls[-1]["outbound_domain_allowlist"] == ("api.openai.com", "github.com")


def test_cli_invalid_volume_reports_json_argument_error(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    with pytest.raises(SystemExit) as exc:
        cli.main(["--volume", "cache-volume:cache", "run", "true"])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["error"]["type"] == "argument_error"
    assert payload["error"]["message"] == "argument --volume: --volume mount path must be absolute"


def test_cli_run_command_uses_argv_api(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(
        [
            "run-command",
            "--cwd",
            "/workspace/app",
            "--env",
            "A=B",
            "python",
            "-c",
            "print(123)",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "python -c 'print(123)'"
    assert payload["stdout"] == "argv ok\n"
    assert FakeSandbox.instances[-1].run_command_calls == [
        ("python", ["-c", "print(123)"], "/workspace/app", {"A": "B"})
    ]


def test_cli_run_command_can_return_command_exit_code(monkeypatch, capsys) -> None:
    class NonzeroSandbox(FakeSandbox):
        def run_command(
            self,
            cmd: str,
            args: list[str] | None = None,
            *,
            cwd: str | None = None,
            env: dict[str, str] | None = None,
            max_output_bytes: int | None = None,
        ) -> CommandResult:
            return CommandResult("false", "", "", 7, 1, max_output_bytes=max_output_bytes)

    NonzeroSandbox.create_calls = []
    NonzeroSandbox.instances = []
    NonzeroSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", NonzeroSandbox)

    exit_code = cli.main(["run-command", "--use-command-exit-code", "false"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 7
    assert payload["exit_code"] == 7


def test_cli_domain_and_snapshot(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    assert cli.main(["--sandbox-id", "sb-123", "domain", "3000"]) == 0
    domain_payload = json.loads(capsys.readouterr().out)
    assert domain_payload == {"port": 3000, "url": "https://sandbox.example/3000"}

    assert cli.main(["--workspace-volume", "workspace-volume", "snapshot"]) == 0
    snapshot_payload = json.loads(capsys.readouterr().out)
    assert snapshot_payload == {
        "kind": "modal_volume",
        "name": "workspace-volume",
        "status": "created",
        "workspace": "/workspace",
    }


def test_cli_snapshot_without_workspace_volume_reports_json_runtime_error(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    with pytest.raises(SystemExit) as exc:
        cli.main(["snapshot"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert exc.value.code == 1
    assert captured.out == ""
    assert payload["status"] == "error"
    assert payload["error"]["type"] == "runtime_error"
    assert payload["error"]["message"] == "create_snapshot requires a string workspace volume."
    assert payload["error"]["next_steps"] == [
        "Run `sandbox doctor` to inspect local setup without creating Modal resources."
    ]


def test_cli_start_creates_sandbox_and_detaches_for_reuse(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.from_id_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(["--image", "python:3.13-slim", "--sandbox-timeout", "600", "start"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {
        "sandbox_id": "sb-fake",
        "sandbox_timeout": 600,
        "status": "started",
        "stop_command": "sandbox stop sb-fake",
        "use_command": 'sandbox --sandbox-id sb-fake run "python --version"',
        "workspace": "/workspace",
    }
    assert FakeSandbox.create_calls[-1]["sandbox_id"] is None
    assert FakeSandbox.instances[-1].detached is True
    assert not hasattr(FakeSandbox.instances[-1], "closed")


def test_cli_stop_terminates_existing_sandbox_without_creating_workspace(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.from_id_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(["stop", "sb-123"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {"sandbox_id": "sb-123", "status": "terminated"}
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.from_id_calls == [
        {
            "app_name": "modal-sandbox-sdk",
            "command_timeout": 30,
            "ensure_workspace": False,
            "max_output_bytes": 10 * 1024 * 1024,
            "sandbox_id": "sb-123",
            "sandbox_timeout": 300,
            "workspace": "/workspace",
        }
    ]
    assert FakeSandbox.instances[-1].terminated is True
    assert not hasattr(FakeSandbox.instances[-1], "closed")


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
    payload = json.loads(captured.err)
    assert payload["status"] == "error"
    assert payload["error"]["type"] == "argument_error"
    assert payload["error"]["message"] == "--env values must use KEY=VALUE"


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
    payload = json.loads(captured.err)
    assert payload["status"] == "error"
    assert payload["error"]["type"] == "modal_authentication_error"
    assert payload["error"]["message"] == "Run modal setup before using Modal sandboxes."
    assert payload["error"]["next_steps"] == [
        "Run `sandbox doctor` to inspect local setup without creating Modal resources."
    ]


def test_cli_missing_write_content_reports_json_argument_error(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    with pytest.raises(SystemExit) as exc:
        cli.main(["write", "game.py"])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["error"]["type"] == "argument_error"
    assert "one of the arguments --content --content-file --stdin is required" in payload["error"]["message"]


def test_cli_write_input_options_are_mutually_exclusive(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    with pytest.raises(SystemExit) as exc:
        cli.main(["write", "game.py", "--content", "x", "--stdin"])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["error"]["type"] == "argument_error"
    assert "not allowed with argument" in payload["error"]["message"]


def test_cli_schema_outputs_machine_readable_metadata_without_creating_sandbox(monkeypatch, capsys) -> None:
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
    assert payload["commands"]["start"]["output"]["sandbox_id"] == "string"
    assert payload["commands"]["stop"]["creates_sandbox"] is False
    assert payload["commands"]["run"]["output"]["stdout"] == "string"
    assert payload["commands"]["run"]["output"]["stdout_truncated"] == "boolean"
    assert payload["commands"]["run-command"]["output"]["stdout"] == "string"
    assert payload["commands"]["domain"]["output"] == {"port": "integer", "url": "string"}
    assert payload["commands"]["snapshot"]["output"]["kind"] == "modal_volume"
    assert payload["commands"]["quickstart"]["creates_sandbox"] is False
    assert payload["commands"]["quickstart"]["output"]["quickstart_command"] == "string"
    assert payload["commands"]["quickstart"]["output"]["quickstart"] == "object when --run is used"
    assert payload["commands"]["doctor"]["output"]["summary"] == "object"
    assert payload["global_options"]["--max-output-bytes"] == (
        "Maximum captured bytes for stdout and stderr separately. Defaults to 10485760."
    )
    assert payload["global_options"]["--runtime"] == (
        "Vercel-style runtime alias. Supported values: python3.13, node24, node22."
    )
    assert payload["global_options"]["--volume NAME:/mount"] == (
        "Modal volume name and absolute sandbox mount path. Repeatable."
    )
    assert payload["global_options"]["--allow-domain DOMAIN"] == (
        "Allow sandbox outbound network access to a domain. Repeatable."
    )
    assert payload["lifecycle"]["volume_mounts"] == (
        "Use --volume NAME:/mount to mount additional Modal volumes at absolute sandbox paths."
    )
    assert payload["lifecycle"]["domain_allowlist"] == (
        "Use --allow-domain DOMAIN to restrict sandbox outbound network access to listed domains."
    )
    assert payload["image_aliases"]["py313"] == "python:3.13-slim"
    assert payload["recommended_first_commands"][0]["command"] == "sandbox schema"
    assert payload["recommended_first_commands"][-1]["command"] == "sandbox quickstart --run"
    assert payload["golden_workflows"][0] == {
        "id": "safe_first_run",
        "purpose": "Inspect local readiness before creating Modal resources.",
        "creates_modal_resources": False,
        "commands": ["sandbox schema", "sandbox doctor", "sandbox quickstart"],
        "success_signal": "quickstart reports ready_to_run or gives setup next steps.",
    }
    persistent_workflow = payload["golden_workflows"][2]
    assert persistent_workflow["id"] == "persistent_workspace_files"
    assert "sandbox --image py313 --workspace-volume work snapshot" in persistent_workflow["commands"]
    assert payload["lifecycle"]["safe_discovery_commands"] == ["schema", "doctor", "quickstart"]
    assert "quickstart --run" in payload["lifecycle"]["live_modal_commands"]
    assert "run-command" in payload["lifecycle"]["live_modal_commands"]
    assert "domain" in payload["lifecycle"]["live_modal_commands"]
    assert "snapshot" in payload["lifecycle"]["live_modal_commands"]
    assert payload["commands"]["schema"]["creates_sandbox"] is False
    assert payload["commands"]["doctor"]["creates_sandbox"] is False
    assert payload["auth"]["setup_commands"][0] == "modal setup"
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.instances == []


def test_cli_schema_contract_pins_commands_lifecycle_and_workflows(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = True
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)
    monkeypatch.setattr(cli, "_package_version", lambda: "0.1.0")

    assert cli.main(["schema"]) == 0

    payload = json.loads(capsys.readouterr().out)
    expected_commands = {
        "start",
        "stop",
        "run",
        "run-command",
        "write",
        "read",
        "ls",
        "mkdir",
        "rm",
        "upload",
        "download",
        "domain",
        "snapshot",
        "schema",
        "doctor",
        "quickstart",
    }
    assert set(payload["commands"]) == expected_commands
    assert payload["schema_version"] == "1"
    assert payload["default_output"] == "json"
    assert payload["path_rules"] == {
        "absolute_paths": "Used as absolute paths inside the sandbox.",
        "relative_paths": "Resolved inside the sandbox workspace.",
        "workspace_escape": "Relative paths using '..' cannot escape the workspace.",
    }
    assert payload["lifecycle"]["safe_discovery_commands"] == ["schema", "doctor", "quickstart"]
    assert set(payload["lifecycle"]["live_modal_commands"]) == (
        expected_commands - {"schema", "doctor", "quickstart"} | {"quickstart --run"}
    )
    assert [workflow["id"] for workflow in payload["golden_workflows"]] == [
        "safe_first_run",
        "short_lived_command",
        "persistent_workspace_files",
        "long_lived_reuse",
    ]
    assert payload["golden_workflows"][0]["creates_modal_resources"] is False
    assert all(workflow["commands"] for workflow in payload["golden_workflows"])
    assert all("success_signal" in workflow for workflow in payload["golden_workflows"])
    for command_name, command_schema in payload["commands"].items():
        assert isinstance(command_schema["creates_sandbox"], bool), command_name
        assert command_schema["summary"], command_name
        assert command_schema["example"], command_name
        assert isinstance(command_schema["output"], dict), command_name
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.instances == []


@pytest.mark.parametrize("argv", [["schema"], ["doctor"], ["quickstart"]])
def test_safe_discovery_commands_never_create_sandboxes(monkeypatch, capsys, tmp_path, argv) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = True
    config_path = tmp_path / ".modal.toml"
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)
    monkeypatch.setattr(cli, "_modal_package_info", lambda: {"installed": True, "version": "1.4.3"})
    monkeypatch.setattr(cli, "_modal_config_path", lambda: config_path)
    monkeypatch.delenv("MODAL_TOKEN_ID", raising=False)
    monkeypatch.delenv("MODAL_TOKEN_SECRET", raising=False)

    assert cli.main(argv) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.instances == []


def test_cli_persistent_golden_workflow_uses_workspace_volume(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)
    common = ["--image", "py313", "--workspace-volume", "work"]

    assert cli.main([*common, "write", "app.py", "--content", "print(123)"]) == 0
    assert cli.main([*common, "run", "python app.py"]) == 0
    assert cli.main([*common, "read", "app.py"]) == 0
    assert cli.main([*common, "snapshot"]) == 0

    capsys.readouterr()
    assert FakeSandbox.create_calls
    assert all(call["volumes"] == (SandboxVolume.workspace("work"),) for call in FakeSandbox.create_calls[-4:])
    assert FakeSandbox.instances[-1].config.volumes == (SandboxVolume.workspace("work"),)


def test_cli_recipes_is_not_a_public_command(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = True
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    with pytest.raises(SystemExit) as error:
        cli.main(["recipes"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert error.value.code == 2
    assert payload["status"] == "error"
    assert payload["error"]["type"] == "argument_error"
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
    assert payload["ready"] is False
    assert payload["status"] == "needs_setup"
    assert payload["problems"] == ["modal_credentials_missing"]
    assert payload["next_steps"] == ["Run `uv run modal setup` before creating a live sandbox."]
    assert payload["modal_package"] == {"installed": True, "version": "1.4.3"}
    assert payload["credentials"]["status"] == "missing_or_unknown"
    assert payload["credentials"]["modal_toml"]["path"] == str(config_path)
    assert payload["recommended_commands"][-1]["command"] == "uv run modal setup"
    assert payload["creates_modal_resources"] is False
    assert payload["setup_commands"][0] == "modal setup"
    assert payload["summary"] == {
        "ready": False,
        "message": "Modal credentials were not found. Run modal setup before creating a sandbox.",
        "next_command": "uv run modal setup",
    }
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.instances == []


def test_cli_doctor_reports_partial_environment_credentials(monkeypatch, capsys, tmp_path) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = True
    config_path = tmp_path / ".modal.toml"
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)
    monkeypatch.setattr(cli, "_modal_package_info", lambda: {"installed": True, "version": "1.4.3"})
    monkeypatch.setattr(cli, "_modal_config_path", lambda: config_path)
    monkeypatch.setenv("MODAL_TOKEN_ID", "token-id")
    monkeypatch.delenv("MODAL_TOKEN_SECRET", raising=False)

    exit_code = cli.main(["doctor"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["ready"] is False
    assert payload["status"] == "needs_setup"
    assert payload["problems"] == ["modal_credentials_partial_environment"]
    assert payload["next_steps"] == ["Set both `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`, or run `uv run modal setup`."]
    assert payload["credentials"]["status"] == "partial_environment"
    assert payload["credentials"]["environment"] == {
        "complete": False,
        "modal_token_id_set": True,
        "modal_token_secret_set": False,
    }
    assert payload["ready_hint"] == (
        "Modal token environment variables are incomplete. Set both token variables before creating a sandbox."
    )
    assert payload["summary"] == {
        "ready": False,
        "message": "Modal token environment variables are incomplete. Set both token variables before creating a sandbox.",
        "next_command": "Set both MODAL_TOKEN_ID and MODAL_TOKEN_SECRET",
    }
    assert payload["recommended_commands"][-1]["command"] == "uv run modal setup"
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.instances == []


def test_cli_doctor_reports_ready_when_credentials_are_configured(monkeypatch, capsys, tmp_path) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = True
    config_path = tmp_path / ".modal.toml"
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)
    monkeypatch.setattr(cli, "_modal_package_info", lambda: {"installed": True, "version": "1.4.3"})
    monkeypatch.setattr(cli, "_modal_config_path", lambda: config_path)
    monkeypatch.setenv("MODAL_TOKEN_ID", "token-id")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "token-secret")

    exit_code = cli.main(["doctor"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["ready"] is True
    assert payload["status"] == "ready"
    assert payload["problems"] == []
    assert payload["next_steps"] == [
        "Run `sandbox quickstart --run` to create a short-lived sandbox and verify execution."
    ]
    assert payload["credentials"]["status"] == "configured_from_environment"
    assert payload["creates_modal_resources"] is False
    assert payload["summary"] == {
        "ready": True,
        "message": "Modal is configured. You can run a live sandbox quickstart.",
        "next_command": "sandbox quickstart --run",
    }
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.instances == []


def test_cli_quickstart_preview_does_not_create_sandbox(monkeypatch, capsys, tmp_path) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = True
    config_path = tmp_path / ".modal.toml"
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)
    monkeypatch.setattr(cli, "_modal_package_info", lambda: {"installed": True, "version": "1.4.3"})
    monkeypatch.setattr(cli, "_modal_config_path", lambda: config_path)
    monkeypatch.delenv("MODAL_TOKEN_ID", raising=False)
    monkeypatch.delenv("MODAL_TOKEN_SECRET", raising=False)

    exit_code = cli.main(["quickstart"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "needs_setup"
    assert payload["creates_modal_resources"] is False
    assert payload["checks"]["ready"] is False
    assert payload["safe_commands"] == ["sandbox schema", "sandbox doctor", "sandbox quickstart"]
    assert payload["live_command"] == "sandbox quickstart --run"
    assert payload["quickstart_command"] == "python -c 'print(123)'"
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.instances == []


def test_cli_quickstart_run_creates_sandbox_and_respects_global_options(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)
    monkeypatch.setattr(cli, "_modal_package_info", lambda: {"installed": True, "version": "1.4.3"})
    monkeypatch.setenv("MODAL_TOKEN_ID", "token-id")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "token-secret")

    exit_code = cli.main(
        [
            "--image",
            "py313",
            "--workspace",
            "/work",
            "--timeout",
            "12",
            "--sandbox-timeout",
            "99",
            "--region",
            "us-east-1",
            "--block-network",
            "quickstart",
            "--run",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "python -c 'print(123)'"
    assert payload["stdout"] == "ok\n"
    assert payload["creates_modal_resources"] is True
    assert payload["quickstart"]["creates_modal_resources"] is True
    assert payload["quickstart"]["checks"]["ready"] is True
    assert FakeSandbox.instances[-1].run_calls == [("python -c 'print(123)'", None)]
    assert FakeSandbox.create_calls == [
        {
            "app_name": "modal-sandbox-sdk",
            "workspace": "/work",
            "image": "python:3.13-slim",
            "runtime": None,
            "volumes": (),
            "env": None,
            "command_timeout": 12,
            "sandbox_timeout": 99,
            "cpu": None,
            "memory": None,
            "gpu": None,
            "region": "us-east-1",
            "block_network": True,
            "max_output_bytes": 10 * 1024 * 1024,
            "encrypted_ports": (),
            "unencrypted_ports": (),
            "sandbox_id": None,
        }
    ]
