from __future__ import annotations

import os

import pytest

from sandbox import Sandbox


pytestmark = pytest.mark.skipif(
    os.environ.get("MODAL_SANDBOX_SDK_RUN_MODAL_TESTS") != "1",
    reason="set MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 to run real Modal integration tests",
)


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
