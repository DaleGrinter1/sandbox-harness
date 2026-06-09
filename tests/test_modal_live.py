from __future__ import annotations

import json
import os
import sys
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from sandbox import Sandbox
from sandbox_cli import cli

live_modal = pytest.mark.skipif(
    os.environ.get("MODAL_SANDBOX_SDK_RUN_MODAL_TESTS") != "1",
    reason="set MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 to run real Modal integration tests",
)


def _unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _run_cli_json(capsys: pytest.CaptureFixture[str], args: list[str]) -> dict[str, Any]:
    exit_code = cli.main(args)
    captured = capsys.readouterr()
    assert captured.err == ""
    assert exit_code == 0
    return json.loads(captured.out)


def _delete_modal_volume(name: str) -> None:
    import modal

    modal.Volume.delete(name)


def test_delete_modal_volume_uses_modal_delete(monkeypatch) -> None:
    deleted: list[str] = []
    fake_modal = SimpleNamespace(Volume=SimpleNamespace(delete=deleted.append))
    monkeypatch.setitem(sys.modules, "modal", fake_modal)

    _delete_modal_volume("modal-sandbox-sdk-workspace-test")

    assert deleted == ["modal-sandbox-sdk-workspace-test"]


@live_modal
def test_modal_sandbox_file_helpers_operate_inside_workspace() -> None:
    with Sandbox.create(
        app_name="modal-sandbox-sdk-live-tests",
        image="python:3.13-slim",
    ) as sandbox:
        sandbox.write_text("game.py", "print('hello from sandbox')\n")
        files = sandbox.list_files(".")
        content = sandbox.read_text("game.py")
        run_result = sandbox.run("python game.py")

    assert "game.py" in files
    assert content == "print('hello from sandbox')\n"
    assert run_result.exit_code == 0
    assert run_result.stdout.strip() == "hello from sandbox"


@live_modal
def test_cli_quickstart_run_acceptance(capsys) -> None:
    payload = _run_cli_json(
        capsys,
        [
            "--app-name",
            _unique_name("modal-sandbox-sdk-live"),
            "--image",
            "py313",
            "quickstart",
            "--run",
        ],
    )

    assert payload["creates_modal_resources"] is True
    assert payload["command"] == "python -c 'print(123)'"
    assert payload["exit_code"] == 0
    assert payload["stdout"].strip() == "123"
    assert payload["quickstart"]["quickstart_command"] == "python -c 'print(123)'"


@live_modal
def test_cli_file_workflow_persists_with_workspace_volume(capsys) -> None:
    app_name = _unique_name("modal-sandbox-sdk-live")
    volume_name = _unique_name("modal-sandbox-sdk-workspace")
    common_args = [
        "--app-name",
        app_name,
        "--image",
        "py313",
        "--workspace-volume",
        volume_name,
    ]

    try:
        write_payload = _run_cli_json(
            capsys,
            [
                *common_args,
                "write",
                "hello.py",
                "--content",
                "print('hello from cli live test')\n",
            ],
        )
        run_payload = _run_cli_json(capsys, [*common_args, "run", "python hello.py"])
        read_payload = _run_cli_json(capsys, [*common_args, "read", "hello.py"])
        files_payload = _run_cli_json(capsys, [*common_args, "ls", "."])
        snapshot_payload = _run_cli_json(capsys, [*common_args, "snapshot"])

        assert write_payload == {"path": "hello.py", "status": "wrote"}
        assert run_payload["exit_code"] == 0
        assert run_payload["stdout"].strip() == "hello from cli live test"
        assert read_payload == {"content": "print('hello from cli live test')\n", "path": "hello.py"}
        assert "hello.py" in files_payload["files"]
        assert snapshot_payload == {
            "kind": "modal_volume",
            "name": volume_name,
            "status": "created",
            "workspace": "/workspace",
        }
    finally:
        _delete_modal_volume(volume_name)


@live_modal
def test_cli_start_reuse_and_stop_acceptance(capsys) -> None:
    sandbox_id = None
    try:
        start_payload = _run_cli_json(
            capsys,
            [
                "--app-name",
                _unique_name("modal-sandbox-sdk-live"),
                "--image",
                "py313",
                "--sandbox-timeout",
                "120",
                "--encrypted-port",
                "3000",
                "start",
            ],
        )
        sandbox_id = str(start_payload["sandbox_id"])

        write_payload = _run_cli_json(
            capsys,
            [
                "--sandbox-id",
                sandbox_id,
                "write",
                "agent.py",
                "--content",
                "print('reused sandbox')\n",
            ],
        )
        run_payload = _run_cli_json(capsys, ["--sandbox-id", sandbox_id, "run", "python agent.py"])
        domain_payload = _run_cli_json(capsys, ["--sandbox-id", sandbox_id, "domain", "3000"])

        assert write_payload == {"path": "agent.py", "status": "wrote"}
        assert run_payload["exit_code"] == 0
        assert run_payload["stdout"].strip() == "reused sandbox"
        assert domain_payload["port"] == 3000
        assert str(domain_payload["url"]).startswith("http")
    finally:
        if sandbox_id is not None:
            stop_payload = _run_cli_json(capsys, ["stop", sandbox_id])
            assert stop_payload == {"sandbox_id": sandbox_id, "status": "terminated"}
