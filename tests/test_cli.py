from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

import pytest
from sandbox import (
    CommandResult,
    ModalAuthenticationError,
    SandboxConfig,
    SandboxFileStat,
    SandboxImageSnapshot,
    SandboxReadinessProbe,
    SandboxSnapshot,
    SandboxVolume,
    SandboxWatchEvent,
)
from sandbox_cli import cli


class FakeSandbox:
    create_calls: list[dict[str, object]] = []
    from_id_calls: list[dict[str, object]] = []
    from_name_calls: list[dict[str, object]] = []
    instances: list[FakeSandbox] = []
    raise_auth_error = False

    @classmethod
    def create(cls, **kwargs: object) -> FakeSandbox:
        if cls.raise_auth_error:
            raise ModalAuthenticationError("Run modal setup before using Modal sandboxes.")
        sandbox_id = kwargs.get("sandbox_id")
        sandbox = cls(sandbox_id=sandbox_id if isinstance(sandbox_id, str) else "sb-fake")
        sandbox_timeout = kwargs.get("sandbox_timeout", 300)
        max_output_bytes = kwargs.get("max_output_bytes")
        sandbox_name = kwargs.get("name")
        tags = kwargs.get("tags")
        volumes = kwargs.get("volumes", ())
        readiness_probe = kwargs.get("readiness_probe")
        if not isinstance(volumes, tuple):
            volumes = ()
        volumes = cast(tuple[SandboxVolume, ...], volumes)
        sandbox.config = SandboxConfig(
            name=sandbox_name if isinstance(sandbox_name, str) else None,
            tags=cast(dict[str, str], tags) if isinstance(tags, dict) else None,
            workspace=str(kwargs.get("workspace", "/workspace")),
            sandbox_timeout=sandbox_timeout if isinstance(sandbox_timeout, int) else 300,
            max_output_bytes=max_output_bytes if isinstance(max_output_bytes, int) else None,
            volumes=volumes,
            readiness_probe=readiness_probe,
        )
        cls.create_calls.append(kwargs)
        cls.instances.append(sandbox)
        return sandbox

    @classmethod
    def from_id(cls, sandbox_id: str, **kwargs: object) -> FakeSandbox:
        sandbox = cls(sandbox_id=sandbox_id)
        workspace = kwargs.get("workspace", "/workspace")
        volumes = kwargs.get("volumes", ())
        if not isinstance(volumes, tuple):
            volumes = ()
        sandbox.config = SandboxConfig(
            app_name=str(kwargs.get("app_name", "modal-sandbox-sdk")),
            workspace=workspace if isinstance(workspace, str) else "/workspace",
            volumes=cast(tuple[SandboxVolume, ...], volumes),
        )
        cls.from_id_calls.append({"sandbox_id": sandbox_id, **kwargs})
        cls.instances.append(sandbox)
        return sandbox

    @classmethod
    def from_name(cls, name: str, **kwargs: object) -> FakeSandbox:
        sandbox = cls(sandbox_id=f"sb-{name}")
        workspace = kwargs.get("workspace", "/workspace")
        sandbox_timeout = kwargs.get("sandbox_timeout", 300)
        max_output_bytes = kwargs.get("max_output_bytes")
        volumes = kwargs.get("volumes", ())
        if not isinstance(volumes, tuple):
            volumes = ()
        sandbox.config = SandboxConfig(
            app_name=str(kwargs.get("app_name", "modal-sandbox-sdk")),
            name=name,
            workspace=workspace if isinstance(workspace, str) else "/workspace",
            volumes=cast(tuple[SandboxVolume, ...], volumes),
            sandbox_timeout=sandbox_timeout if isinstance(sandbox_timeout, int) else 300,
            max_output_bytes=max_output_bytes if isinstance(max_output_bytes, int) else None,
        )
        cls.from_name_calls.append({"name": name, **kwargs})
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
        self.snapshot_filesystem_calls: list[tuple[int, int | None]] = []
        self.snapshot_directory_calls: list[tuple[str, int, int | None]] = []
        self.mount_image_calls: list[tuple[str, object]] = []
        self.unmount_image_calls: list[str] = []
        self.stat_calls: list[str] = []
        self.watch_calls: list[tuple[str, bool, int | None, list[str] | None]] = []
        self.seed_git_calls: list[tuple[str, str, str | None, int]] = []
        self.seed_tarball_calls: list[tuple[str, str, int]] = []
        self.wait_ready_calls: list[int] = []
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

    def workspace_checkpoint(self) -> SandboxSnapshot:
        return self.create_snapshot()

    def snapshot_filesystem(self, *, timeout: int = 55, ttl: int | None = 30 * 24 * 3600) -> SandboxImageSnapshot:
        self.snapshot_filesystem_calls.append((timeout, ttl))
        return SandboxImageSnapshot(image_id="im-filesystem", kind="modal_filesystem", ttl_seconds=ttl)

    def snapshot_directory(
        self, path: str, *, timeout: int = 55, ttl: int | None = 30 * 24 * 3600
    ) -> SandboxImageSnapshot:
        self.snapshot_directory_calls.append((path, timeout, ttl))
        return SandboxImageSnapshot(
            image_id="im-directory", kind="modal_directory", path="/workspace/src", ttl_seconds=ttl
        )

    def mount_image(self, path: str, image: object) -> None:
        self.mount_image_calls.append((path, image))

    def unmount_image(self, path: str) -> None:
        self.unmount_image_calls.append(path)

    def stat(self, path: str) -> SandboxFileStat:
        self.stat_calls.append(path)
        return SandboxFileStat(path="/workspace/game.py", kind="file", size=12, permissions="644")

    def watch(
        self,
        path: str,
        *,
        recursive: bool = False,
        timeout: int | None = None,
        filter: list[str] | None = None,
    ) -> list[SandboxWatchEvent]:
        self.watch_calls.append((path, recursive, timeout, filter))
        return [SandboxWatchEvent(path="/workspace/game.py", event_type="Modify")]

    def sync_workspace(self) -> CommandResult:
        return self.run_command("sync", [self.config.workspace])

    def wait_until_ready(self, *, timeout: int = 300) -> None:
        self.wait_ready_calls.append(timeout)

    def seed_git(
        self,
        repo_url: str,
        *,
        destination: str = ".",
        ref: str | None = None,
        depth: int = 1,
    ) -> CommandResult:
        self.seed_git_calls.append((repo_url, destination, ref, depth))
        return self.run_command("git", ["clone", repo_url, destination])

    def seed_tarball(
        self,
        tarball_url: str,
        *,
        destination: str = ".",
        strip_components: int = 1,
    ) -> CommandResult:
        self.seed_tarball_calls.append((tarball_url, destination, strip_components))
        return self.run_command("python", ["-c", "extract", tarball_url, destination, str(strip_components)])


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
            "readiness_probe": None,
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


def test_cli_create_accepts_name_and_tags(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(
        [
            "--name",
            "agent-workspace",
            "--tag",
            "kind=frontend",
            "--tag",
            "owner=team",
            "run",
            "python -c 'print(123)'",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["stdout"] == "ok\n"
    assert FakeSandbox.create_calls[-1]["name"] == "agent-workspace"
    assert FakeSandbox.create_calls[-1]["tags"] == {"kind": "frontend", "owner": "team"}


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


def test_cli_create_accepts_cidr_allowlists(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(
        [
            "--allow-cidr",
            "10.0.0.0/8",
            "--allow-inbound-cidr",
            "203.0.113.0/24",
            "run",
            "python -c 'print(123)'",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["stdout"] == "ok\n"
    assert FakeSandbox.create_calls[-1]["outbound_cidr_allowlist"] == ("10.0.0.0/8",)
    assert FakeSandbox.create_calls[-1]["inbound_cidr_allowlist"] == ("203.0.113.0/24",)


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


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--workspace", "workspace", "run", "true"], "argument --workspace: value must be an absolute sandbox path"),
        (["--timeout", "0", "run", "true"], "argument --timeout: value must be a positive integer"),
        (
            ["--sandbox-timeout", "-1", "run", "true"],
            "argument --sandbox-timeout: value must be a positive integer",
        ),
        (["--cpu", "0", "run", "true"], "argument --cpu: value must be a positive number"),
        (["--memory", "0", "run", "true"], "argument --memory: value must be a positive integer"),
        (
            ["--name", "bad name", "run", "true"],
            "argument --name: sandbox name may only contain letters, numbers, dashes, periods, and underscores",
        ),
        (
            ["--name", "a" * 64, "run", "true"],
            "argument --name: sandbox name must be shorter than 64 characters",
        ),
        (["--tag", "missing-equals", "run", "true"], "argument --tag: --tag values must use KEY=VALUE"),
        (["--tag", "=value", "run", "true"], "argument --tag: --tag keys must not be empty"),
        (
            ["--max-output-bytes", "-1", "run", "true"],
            "argument --max-output-bytes: value must be a non-negative integer",
        ),
        (
            ["--encrypted-port", "65536", "run", "true"],
            "argument --encrypted-port: port must be an integer between 1 and 65535",
        ),
        (["--allow-domain", "", "run", "true"], "argument --allow-domain: value must not be empty"),
        (
            ["--allow-domain", "https://api.openai.com", "run", "true"],
            "argument --allow-domain: value must be a hostname, not a URL",
        ),
        (["--allow-cidr", "10.0.0.1", "run", "true"], "argument --allow-cidr: value must be a CIDR range"),
        (
            ["--allow-inbound-cidr", "not-a-cidr/24", "run", "true"],
            "argument --allow-inbound-cidr: value must be a valid CIDR range",
        ),
        (
            ["--block-network", "--allow-domain", "api.openai.com", "run", "true"],
            "--block-network cannot be combined with --allow-domain, --allow-cidr, or --allow-inbound-cidr",
        ),
        (
            ["--sandbox-id", "sb-123", "--sandbox-name", "agent-workspace", "run", "true"],
            "--sandbox-id cannot be used with --sandbox-name",
        ),
        (
            ["--name", "new-workspace", "--sandbox-name", "agent-workspace", "run", "true"],
            "--name cannot be used with --sandbox-name",
        ),
        (
            ["--sandbox-id", "sb-123", "--readiness-tcp", "3000", "run", "true"],
            "readiness probe flags only apply when creating a sandbox",
        ),
        (
            ["--wait-ready", "run", "true"],
            "--wait-ready requires --readiness-tcp, --readiness-exec, --sandbox-id, or --sandbox-name",
        ),
        (["wait-ready"], "wait-ready requires --sandbox-id or --sandbox-name"),
        (
            ["--readiness-tcp", "3000", "wait-ready"],
            "readiness probe flags cannot be combined with wait-ready",
        ),
        (
            ["--readiness-tcp", "3000", "quickstart"],
            "readiness flags require quickstart --run or an operational command",
        ),
        (["watch", ".", "--timeout", "0"], "argument --timeout: value must be a positive integer"),
        (
            ["watch", ".", "--timeout", "1", "--event", "bad/event"],
            "argument --event: watch event names may only contain letters, numbers, dashes, and underscores",
        ),
        (["seed-git", "git@github.com:example/project.git"], "argument url: URL must be HTTP(S)"),
        (
            ["seed-tarball", "https://user:token@example.com/archive.tar.gz"],
            "argument url: URL must not include embedded credentials",
        ),
    ],
)
def test_cli_invalid_global_configuration_reports_argument_error_without_creating_sandbox(
    monkeypatch, capsys, argv, message
) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    with pytest.raises(SystemExit) as exc:
        cli.main(argv)

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["error"]["type"] == "argument_error"
    assert payload["error"]["message"] == message
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.instances == []


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


def test_cli_run_can_attach_to_named_sandbox(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.from_name_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(["--sandbox-name", "agent-workspace", "run", "python --version"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["stdout"] == "ok\n"
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.from_name_calls == [
        {
            "name": "agent-workspace",
            "app_name": "modal-sandbox-sdk",
            "workspace": "/workspace",
            "command_timeout": 30,
            "sandbox_timeout": 300,
            "max_output_bytes": 10 * 1024 * 1024,
        }
    ]


def test_cli_domain_and_snapshot(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    assert cli.main(["--sandbox-id", "sb-123", "domain", "3000"]) == 0
    domain_payload = json.loads(capsys.readouterr().out)
    assert domain_payload == {"port": 3000, "url": "https://sandbox.example/3000"}

    assert cli.main(["--sandbox-name", "agent-workspace", "domain", "3000"]) == 0
    named_domain_payload = json.loads(capsys.readouterr().out)
    assert named_domain_payload == {"port": 3000, "url": "https://sandbox.example/3000"}
    assert FakeSandbox.from_name_calls[-1]["name"] == "agent-workspace"

    assert cli.main(["--workspace-volume", "workspace-volume", "snapshot"]) == 0
    snapshot_payload = json.loads(capsys.readouterr().out)
    assert snapshot_payload == {
        "kind": "modal_volume",
        "name": "workspace-volume",
        "status": "created",
        "workspace": "/workspace",
    }


def test_cli_modal_native_snapshot_mount_and_unmount(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    assert cli.main(["snapshot-filesystem", "--timeout", "7", "--no-ttl"]) == 0
    filesystem_payload = json.loads(capsys.readouterr().out)
    assert filesystem_payload == {
        "image_id": "im-filesystem",
        "kind": "modal_filesystem",
        "path": None,
        "status": "created",
        "ttl_seconds": None,
    }
    assert FakeSandbox.instances[-1].snapshot_filesystem_calls == [(7, None)]

    assert cli.main(["snapshot-directory", "src", "--timeout", "8", "--ttl", "60"]) == 0
    directory_payload = json.loads(capsys.readouterr().out)
    assert directory_payload == {
        "image_id": "im-directory",
        "kind": "modal_directory",
        "path": "/workspace/src",
        "status": "created",
        "ttl_seconds": 60,
    }
    assert FakeSandbox.instances[-1].snapshot_directory_calls == [("src", 8, 60)]

    assert cli.main(["--sandbox-id", "sb-123", "mount-image", "snapshots/src", "im-directory"]) == 0
    mount_payload = json.loads(capsys.readouterr().out)
    assert mount_payload == {"image_id": "im-directory", "path": "snapshots/src", "status": "mounted"}
    assert FakeSandbox.instances[-1].mount_image_calls == [("snapshots/src", "im-directory")]

    assert cli.main(["--sandbox-id", "sb-123", "unmount-image", "snapshots/src"]) == 0
    unmount_payload = json.loads(capsys.readouterr().out)
    assert unmount_payload == {"path": "snapshots/src", "status": "unmounted"}
    assert FakeSandbox.instances[-1].unmount_image_calls == ["snapshots/src"]


def test_cli_stat_watch_sync_and_source_seed(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    assert cli.main(["stat", "game.py"]) == 0
    stat_payload = json.loads(capsys.readouterr().out)
    assert stat_payload == {
        "kind": "file",
        "modified_time": None,
        "path": "/workspace/game.py",
        "permissions": "644",
        "size": 12,
    }
    assert FakeSandbox.instances[-1].stat_calls == ["game.py"]

    assert cli.main(["watch", ".", "--timeout", "5", "--recursive", "--event", "Modify"]) == 0
    watch_payload = json.loads(capsys.readouterr().out)
    assert watch_payload == {
        "events": [{"event_type": "Modify", "path": "/workspace/game.py"}],
        "path": ".",
        "recursive": True,
        "timeout": 5,
    }
    assert FakeSandbox.instances[-1].watch_calls == [(".", True, 5, ["Modify"])]

    assert cli.main(["--workspace-volume", "work", "sync"]) == 0
    sync_payload = json.loads(capsys.readouterr().out)
    assert sync_payload["stdout"] == "argv ok\n"
    assert FakeSandbox.instances[-1].run_command_calls == [("sync", ["/workspace"], None, None)]
    assert FakeSandbox.create_calls[-1]["volumes"] == (SandboxVolume.workspace("work"),)

    assert cli.main(["seed-git", "https://github.com/example/project.git", "--dest", "src", "--ref", "main"]) == 0
    git_payload = json.loads(capsys.readouterr().out)
    assert git_payload["stdout"] == "argv ok\n"
    assert FakeSandbox.instances[-1].seed_git_calls == [("https://github.com/example/project.git", "src", "main", 1)]

    assert cli.main(["seed-tarball", "https://example.com/archive.tar.gz", "--strip-components", "2"]) == 0
    tarball_payload = json.loads(capsys.readouterr().out)
    assert tarball_payload["stdout"] == "argv ok\n"
    assert FakeSandbox.instances[-1].seed_tarball_calls == [("https://example.com/archive.tar.gz", ".", 2)]


def test_cli_sync_with_attached_sandbox_uses_supplied_workspace_volume(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    assert cli.main(["--sandbox-id", "sb-123", "--workspace-volume", "work", "sync"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["stdout"] == "argv ok\n"
    assert FakeSandbox.create_calls[-1]["sandbox_id"] == "sb-123"
    assert FakeSandbox.create_calls[-1]["volumes"] == (SandboxVolume.workspace("work"),)
    assert FakeSandbox.instances[-1].config.volumes == (SandboxVolume.workspace("work"),)


def test_cli_snapshot_without_workspace_volume_reports_json_argument_error_without_creating_sandbox(
    monkeypatch, capsys
) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    with pytest.raises(SystemExit) as exc:
        cli.main(["snapshot"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert exc.value.code == 2
    assert captured.out == ""
    assert payload["status"] == "error"
    assert payload["error"]["type"] == "argument_error"
    assert payload["error"]["message"] == "snapshot requires --workspace-volume"
    assert payload["error"]["next_steps"] == [
        "Run `sandbox doctor` to inspect local setup without creating Modal resources."
    ]
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.instances == []


def test_cli_sync_without_workspace_volume_reports_json_argument_error_without_creating_sandbox(
    monkeypatch, capsys
) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    with pytest.raises(SystemExit) as exc:
        cli.main(["sync"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert exc.value.code == 2
    assert captured.out == ""
    assert payload["status"] == "error"
    assert payload["error"]["type"] == "argument_error"
    assert payload["error"]["message"] == "sync requires --workspace-volume"
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.instances == []


def test_cli_domain_without_sandbox_id_reports_json_argument_error_without_creating_sandbox(
    monkeypatch, capsys
) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    with pytest.raises(SystemExit) as exc:
        cli.main(["--encrypted-port", "3000", "domain", "3000"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert exc.value.code == 2
    assert captured.out == ""
    assert payload["status"] == "error"
    assert payload["error"]["type"] == "argument_error"
    assert payload["error"]["message"] == "domain requires --sandbox-id or --sandbox-name from a started sandbox"
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.instances == []


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


def test_cli_start_can_create_named_sandbox(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(["--name", "agent-workspace", "--image", "python:3.13-slim", "start"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {
        "sandbox_id": "sb-fake",
        "sandbox_name": "agent-workspace",
        "sandbox_timeout": 300,
        "status": "started",
        "stop_command": "sandbox --sandbox-name agent-workspace stop",
        "use_command": 'sandbox --sandbox-name agent-workspace run "python --version"',
        "workspace": "/workspace",
    }
    assert FakeSandbox.create_calls[-1]["name"] == "agent-workspace"
    assert FakeSandbox.instances[-1].detached is True


def test_cli_start_can_wait_for_tcp_readiness(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(
        [
            "--encrypted-port",
            "3000",
            "--readiness-tcp",
            "3000",
            "--readiness-interval-ms",
            "250",
            "--wait-ready",
            "--ready-timeout",
            "45",
            "start",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    probe = FakeSandbox.create_calls[-1]["readiness_probe"]
    assert exit_code == 0
    assert payload["ready"] is True
    assert isinstance(probe, SandboxReadinessProbe)
    assert probe.to_dict() == {"command": (), "interval_ms": 250, "kind": "tcp", "port": 3000}
    assert FakeSandbox.instances[-1].wait_ready_calls == [45]
    assert FakeSandbox.instances[-1].detached is True


def test_cli_run_can_wait_for_exec_readiness(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(
        [
            "--readiness-exec",
            "sh -c 'test -f /tmp/ready'",
            "--wait-ready",
            "run",
            "python -c 'print(123)'",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    probe = FakeSandbox.create_calls[-1]["readiness_probe"]
    assert exit_code == 0
    assert payload["stdout"] == "ok\n"
    assert isinstance(probe, SandboxReadinessProbe)
    assert probe.to_dict() == {
        "command": ("sh", "-c", "test -f /tmp/ready"),
        "interval_ms": 100,
        "kind": "exec",
        "port": None,
    }
    assert FakeSandbox.instances[-1].wait_ready_calls == [300]
    assert FakeSandbox.instances[-1].run_calls == [("python -c 'print(123)'", None)]


def test_cli_wait_ready_attaches_to_existing_sandbox(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(["--sandbox-id", "sb-123", "wait-ready", "--timeout", "60"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {"sandbox_id": "sb-123", "status": "ready", "timeout": 60}
    assert FakeSandbox.instances[-1].wait_ready_calls == [60]


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


def test_cli_stop_can_terminate_named_sandbox(monkeypatch, capsys) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.from_name_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = False
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)

    exit_code = cli.main(["--sandbox-name", "agent-workspace", "stop"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {"sandbox_id": "sb-agent-workspace", "sandbox_name": "agent-workspace", "status": "terminated"}
    assert FakeSandbox.create_calls == []
    assert FakeSandbox.from_name_calls == [
        {
            "name": "agent-workspace",
            "app_name": "modal-sandbox-sdk",
            "workspace": "/workspace",
            "command_timeout": 30,
            "sandbox_timeout": 300,
            "max_output_bytes": 10 * 1024 * 1024,
            "ensure_workspace": False,
        }
    ]
    assert FakeSandbox.instances[-1].terminated is True


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
    assert "one of the arguments" in payload["error"]["message"]
    assert "required" in payload["error"]["message"]


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
    assert payload["commands"]["wait-ready"]["output"]["status"] == "ready"
    assert payload["commands"]["snapshot"]["output"]["kind"] == "modal_volume"
    assert payload["commands"]["snapshot-filesystem"]["output"]["kind"] == "modal_filesystem"
    assert payload["commands"]["snapshot-directory"]["output"]["kind"] == "modal_directory"
    assert payload["commands"]["mount-image"]["output"]["status"] == "mounted"
    assert payload["commands"]["unmount-image"]["output"]["status"] == "unmounted"
    assert payload["commands"]["stat"]["output"]["kind"] == "string"
    assert payload["commands"]["watch"]["output"]["events"] == "object[]"
    assert payload["commands"]["sync"]["output"]["stdout"] == "string"
    assert payload["commands"]["seed-git"]["arguments"]["url"] == "Public HTTP(S) Git repository URL."
    assert payload["commands"]["seed-tarball"]["options"]["--strip-components N"] == (
        "Leading archive path components to remove."
    )
    assert payload["commands"]["dry"]["creates_sandbox"] is False
    assert payload["commands"]["dry"]["output"]["status"] == "string"
    assert payload["commands"]["dry"]["output"]["dry_commands"] == "string[]"
    assert payload["commands"]["dry"]["output"]["next_steps"] == "string[]"
    assert payload["commands"]["quickstart"]["creates_sandbox"] is False
    assert payload["commands"]["quickstart"]["output"]["quickstart_command"] == "string"
    assert payload["commands"]["quickstart"]["output"]["quickstart"] == "object when --run is used"
    assert payload["commands"]["doctor"]["output"]["summary"] == "object"
    assert payload["global_options"]["--max-output-bytes"] == (
        "Maximum captured bytes for stdout and stderr separately. Defaults to 10485760; use 0 to capture no bytes."
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
    assert payload["global_options"]["--allow-cidr CIDR"] == (
        "Allow sandbox outbound network access to a CIDR range. Repeatable."
    )
    assert payload["global_options"]["--allow-inbound-cidr CIDR"] == (
        "Allow inbound tunnel/connect-token access from a CIDR range. Repeatable."
    )
    assert payload["global_options"]["--readiness-tcp PORT"] == "Create a sandbox with a Modal TCP readiness probe."
    assert payload["global_options"]["--readiness-exec COMMAND"] == (
        "Create a sandbox with a Modal exec readiness probe parsed into argv."
    )
    assert payload["global_options"]["--wait-ready"] == ("Wait for readiness before running an operational command.")
    assert payload["lifecycle"]["volume_mounts"] == (
        "Use --volume NAME:/mount to mount additional Modal volumes at absolute sandbox paths."
    )
    assert payload["lifecycle"]["domain_allowlist"] == (
        "Use --allow-domain DOMAIN to restrict sandbox outbound network access to listed domains."
    )
    assert payload["lifecycle"]["cidr_allowlists"] == (
        "Use --allow-cidr CIDR for outbound IP ranges and --allow-inbound-cidr CIDR for inbound tunnel/connect-token ranges."
    )
    assert payload["lifecycle"]["preflight_validation"] == (
        "Invalid lifecycle combinations and global configuration are rejected before sandbox creation."
    )
    assert payload["image_aliases"]["py313"] == "python:3.13-slim"
    assert payload["recommended_first_commands"][0]["command"] == "sandbox dry"
    assert payload["recommended_first_commands"][1]["command"] == "sandbox schema"
    assert payload["recommended_first_commands"][-1]["command"] == "sandbox quickstart --run"
    assert payload["golden_workflows"][0] == {
        "id": "safe_first_run",
        "purpose": "Inspect local readiness before creating Modal resources.",
        "creates_modal_resources": False,
        "commands": ["sandbox dry", "sandbox schema", "sandbox doctor", "sandbox quickstart"],
        "success_signal": "quickstart reports ready_to_run or gives setup next steps.",
    }
    persistent_workflow = payload["golden_workflows"][2]
    assert persistent_workflow["id"] == "persistent_workspace_files"
    assert "sandbox --image py313 --workspace-volume work snapshot" in persistent_workflow["commands"]
    assert payload["lifecycle"]["safe_discovery_commands"] == ["dry", "schema", "doctor", "quickstart"]
    assert "quickstart --run" in payload["lifecycle"]["live_modal_commands"]
    assert "run-command" in payload["lifecycle"]["live_modal_commands"]
    assert "domain" in payload["lifecycle"]["live_modal_commands"]
    assert "wait-ready" in payload["lifecycle"]["live_modal_commands"]
    assert "snapshot" in payload["lifecycle"]["live_modal_commands"]
    assert "snapshot-filesystem" in payload["lifecycle"]["live_modal_commands"]
    assert "snapshot-directory" in payload["lifecycle"]["live_modal_commands"]
    assert "stat" in payload["lifecycle"]["live_modal_commands"]
    assert "watch" in payload["lifecycle"]["live_modal_commands"]
    assert "sync" in payload["lifecycle"]["live_modal_commands"]
    assert "seed-git" in payload["lifecycle"]["live_modal_commands"]
    assert "seed-tarball" in payload["lifecycle"]["live_modal_commands"]
    assert payload["lifecycle"]["dry_commands"] == ["dry", "schema", "doctor", "quickstart"]
    assert payload["commands"]["dry"]["creates_sandbox"] is False
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
        "wait-ready",
        "snapshot",
        "snapshot-filesystem",
        "snapshot-directory",
        "mount-image",
        "unmount-image",
        "stat",
        "watch",
        "sync",
        "seed-git",
        "seed-tarball",
        "dry",
        "schema",
        "doctor",
        "quickstart",
        "auth",
    }
    assert set(payload["commands"]) == expected_commands
    assert payload["schema_version"] == "1"
    assert payload["default_output"] == "json"
    assert payload["path_rules"] == {
        "absolute_paths": "Used as absolute paths inside the sandbox.",
        "relative_paths": "Resolved inside the sandbox workspace.",
        "workspace_escape": "Relative paths using '..' cannot escape the workspace.",
    }
    assert payload["lifecycle"]["safe_discovery_commands"] == ["dry", "schema", "doctor", "quickstart"]
    assert payload["lifecycle"]["dry_commands"] == ["dry", "schema", "doctor", "quickstart"]
    assert set(payload["lifecycle"]["live_modal_commands"]) == (
        expected_commands - {"dry", "schema", "doctor", "quickstart", "auth"} | {"quickstart --run"}
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


def test_generated_cli_schema_matches_runtime_contract() -> None:
    generated_schema = json.loads(Path("docs/generated/cli-schema.json").read_text(encoding="utf-8"))

    assert generated_schema == cli._schema_payload()


@pytest.mark.parametrize("argv", [["--dry"], ["dry"], ["schema"], ["doctor"], ["quickstart"]])
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


def test_cli_dry_outputs_discovery_metadata_without_creating_sandbox(monkeypatch, capsys, tmp_path) -> None:
    FakeSandbox.create_calls = []
    FakeSandbox.instances = []
    FakeSandbox.raise_auth_error = True
    config_path = tmp_path / ".modal.toml"
    monkeypatch.setattr(cli, "Sandbox", FakeSandbox)
    monkeypatch.setattr(cli, "_modal_package_info", lambda: {"installed": True, "version": "1.4.3"})
    monkeypatch.setattr(cli, "_modal_config_path", lambda: config_path)
    monkeypatch.delenv("MODAL_TOKEN_ID", raising=False)
    monkeypatch.delenv("MODAL_TOKEN_SECRET", raising=False)

    exit_code = cli.main(["--dry"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "needs_setup"
    assert payload["creates_modal_resources"] is False
    assert payload["dry_commands"] == ["dry", "schema", "doctor", "quickstart"]
    assert payload["safe_commands"] == ["sandbox dry", "sandbox schema", "sandbox doctor", "sandbox quickstart"]
    assert payload["recommended_next_command"] == "sandbox quickstart"
    assert payload["live_command"] == "sandbox quickstart --run"
    assert payload["checks"]["ready"] is False
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
        "environment_vars_set": False,
        "modal_token_id_set": True,
        "modal_token_secret_set": False,
    }
    assert payload["credentials"]["authenticated"] is False
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


def test_cli_auth_writes_modal_toml(monkeypatch, capsys, tmp_path) -> None:
    config_path = tmp_path / ".modal.toml"
    monkeypatch.setattr(cli, "_modal_config_path", lambda: config_path)

    exit_code = cli.main(["auth", "--token-id", "ak-test", "--token-secret", "as-test"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "configured"
    assert payload["profile"] == "default"
    assert payload["config_path"] == str(config_path)
    assert payload["creates_modal_resources"] is False
    content = config_path.read_text()
    assert 'token_id = "ak-test"' in content
    assert 'token_secret = "as-test"' in content
    assert "[default]" in content


def test_cli_auth_custom_profile(monkeypatch, capsys, tmp_path) -> None:
    config_path = tmp_path / ".modal.toml"
    monkeypatch.setattr(cli, "_modal_config_path", lambda: config_path)

    exit_code = cli.main(["auth", "--token-id", "ak-ci", "--token-secret", "as-ci", "--profile", "ci"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["profile"] == "ci"
    content = config_path.read_text()
    assert "[ci]" in content
    assert 'token_id = "ak-ci"' in content


def test_cli_auth_errors_when_profile_exists_without_force(monkeypatch, capsys, tmp_path) -> None:
    config_path = tmp_path / ".modal.toml"
    config_path.write_text('[default]\ntoken_id = "old-id"\ntoken_secret = "old-secret"\n', encoding="utf-8")
    monkeypatch.setattr(cli, "_modal_config_path", lambda: config_path)

    with pytest.raises(SystemExit) as exc:
        cli.main(["auth", "--token-id", "ak-new", "--token-secret", "as-new"])

    assert exc.value.code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["error"]["type"] == "auth_error"
    assert "already exists" in payload["error"]["message"]
    assert "--force" in payload["error"]["message"]
    # Original credentials untouched
    assert 'token_id = "old-id"' in config_path.read_text()


def test_cli_auth_force_overwrites_existing_profile(monkeypatch, capsys, tmp_path) -> None:
    config_path = tmp_path / ".modal.toml"
    config_path.write_text('[default]\ntoken_id = "old-id"\ntoken_secret = "old-secret"\n', encoding="utf-8")
    monkeypatch.setattr(cli, "_modal_config_path", lambda: config_path)

    exit_code = cli.main(["auth", "--token-id", "ak-new", "--token-secret", "as-new", "--force"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "configured"
    content = config_path.read_text()
    assert 'token_id = "ak-new"' in content
    assert "old-id" not in content


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
    assert payload["safe_commands"] == ["sandbox dry", "sandbox schema", "sandbox doctor", "sandbox quickstart"]
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
            "readiness_probe": None,
            "sandbox_id": None,
        }
    ]
