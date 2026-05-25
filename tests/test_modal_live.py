from __future__ import annotations

import os

import pytest

from modal_agent_sandbox import Sandbox


pytestmark = pytest.mark.skipif(
    os.environ.get("SANDBOX_HARNESS_RUN_MODAL_TESTS") != "1",
    reason="set SANDBOX_HARNESS_RUN_MODAL_TESTS=1 to run real Modal integration tests",
)


def test_modal_sandbox_file_helpers_operate_inside_workspace() -> None:
    with Sandbox.create(
        app_name="modal-agent-sandbox-live-tests",
        volume_name=None,
        use_volume=False,
    ) as sandbox:
        write_result = sandbox.write_file("game.py", "print('hello from sandbox')\n")
        files = sandbox.list_files(".")
        content = sandbox.read_file("game.py")
        run_result = sandbox.run("python game.py")

    assert write_result.exit_code == 0
    assert "game.py" in files
    assert content == "print('hello from sandbox')\n"
    assert run_result.exit_code == 0
    assert run_result.stdout.strip() == "hello from sandbox"
