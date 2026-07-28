from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def test_plugin_copy_is_self_contained_and_runs_outside_checkout(tmp_path: Path) -> None:
    source = Path("plugins/modal-sandbox").resolve()
    installed = tmp_path / "installed-plugin"
    unrelated = tmp_path / "unrelated-working-directory"
    shutil.copytree(source, installed)
    unrelated.mkdir()

    manifest = json.loads((installed / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    assert manifest["repository"] == "https://github.com/DaleGrinter1/sandbox-harness"
    assert (installed / "scripts/preflight.py").is_file()
    assert (installed / "scripts/benchmark.py").is_file()
    assert (installed / "scripts/workflow.py").is_file()
    assert (installed / "examples/python-json-workflow.json").is_file()
    assert (installed / "examples/run-tests-safely.json").is_file()

    completed = subprocess.run(
        [
            sys.executable,
            str(installed / "scripts/benchmark.py"),
            str(installed / "examples/python-json-workflow.json"),
            "--validate-only",
        ],
        cwd=unrelated,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["status"] == "valid"

    workflow_completed = subprocess.run(
        [
            sys.executable,
            str(installed / "scripts/workflow.py"),
            str(installed / "examples/run-tests-safely.json"),
            "--validate-only",
        ],
        cwd=unrelated,
        check=False,
        capture_output=True,
        text=True,
    )

    assert workflow_completed.returncode == 0, workflow_completed.stderr
    assert json.loads(workflow_completed.stdout)["status"] == "valid"


def test_distributed_plugin_has_no_repository_runtime_paths() -> None:
    plugin_root = Path("plugins/modal-sandbox")
    forbidden = ("uv run sandbox", "packages/sandbox", "packages/sandbox_cli", "scripts/dev/")

    for path in plugin_root.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".py", ".json", ".yaml"}:
            text = path.read_text(encoding="utf-8")
            for value in forbidden:
                assert value not in text, f"{path} contains repository-only runtime path {value!r}"
