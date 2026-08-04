from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _fake_sandbox(tmp_path: Path) -> Path:
    implementation = tmp_path / "fake_sandbox.py"
    implementation.write_text(
        """
import json
import sys

arguments = sys.argv[1:]
if arguments == ["--version"]:
    print("sandbox 0.4.1")
elif arguments == ["doctor"]:
    print(json.dumps({"credentials": {"complete": True, "verified": False}}))
elif arguments == ["schema", "--agent"]:
    print(json.dumps({
        "schema_version": "1",
        "live_modal": {
            "commands": [
                "cleanup", "domain", "read", "run", "seed-git", "seed-tarball",
                "snapshot", "snapshot-filesystem", "start", "stat", "stop",
                "sync", "wait-ready", "watch", "write"
            ]
        },
        "resource_management": {
            "status_command": "sandbox status",
            "cleanup_preview": "sandbox cleanup --app NAME"
        }
    }))
else:
    print(json.dumps({"schema_version": "1", "creates_modal_resources": False}))
""".lstrip(),
        encoding="utf-8",
    )
    if os.name == "nt":
        executable = tmp_path / "fake-sandbox.cmd"
        executable.write_text(f'@"{sys.executable}" "{implementation}" %*\n', encoding="utf-8")
    else:
        executable = tmp_path / "fake-sandbox"
        executable.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{implementation}" "$@"\n',
            encoding="utf-8",
        )
        executable.chmod(0o755)
    return executable


def test_plugin_copy_is_self_contained_and_runs_outside_checkout(tmp_path: Path, monkeypatch) -> None:
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
    assert (installed / "scripts/evaluate.py").is_file()
    assert (installed / "examples/python-json-workflow.json").is_file()
    assert (installed / "examples/run-tests-safely.json").is_file()
    assert (installed / "skills/modal-sandbox/references/workflow-recipes.md").is_file()
    assert (installed / "skills/modal-sandbox/references/results-and-recovery.md").is_file()

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

    fake_sandbox = _fake_sandbox(tmp_path)
    compatibility_completed = subprocess.run(
        [
            sys.executable,
            str(installed / "scripts/workflow.py"),
            str(installed / "examples/run-tests-safely.json"),
            "--check-compatibility",
            "--sandbox-executable",
            str(fake_sandbox),
        ],
        cwd=unrelated,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compatibility_completed.returncode == 0, compatibility_completed.stderr
    assert json.loads(compatibility_completed.stdout)["status"] == "ready"

    workflow_spec = importlib.util.spec_from_file_location(
        "installed_modal_sandbox_workflow",
        installed / "scripts/workflow.py",
    )
    assert workflow_spec is not None and workflow_spec.loader is not None
    workflow_module = importlib.util.module_from_spec(workflow_spec)
    sys.modules[workflow_spec.name] = workflow_module
    workflow_spec.loader.exec_module(workflow_module)
    monkeypatch.chdir(unrelated)
    preflight = {
        "ok": True,
        "ready_for_live": True,
        "checks": {
            "schema": {
                "schema_version": "1",
                "live_modal": {
                    "commands": [
                        "domain",
                        "read",
                        "run",
                        "seed-git",
                        "seed-tarball",
                        "snapshot",
                        "snapshot-filesystem",
                        "start",
                        "stat",
                        "stop",
                        "sync",
                        "wait-ready",
                        "watch",
                        "write",
                    ]
                },
                "resource_management": {
                    "status_command": "sandbox status",
                    "cleanup_preview": "sandbox cleanup --app NAME",
                },
            }
        },
    }
    workflow_any: Any = workflow_module
    workflow_any._load_preflight_module = lambda: type(
        "FakePreflight",
        (),
        {"run_preflight": staticmethod(lambda *args, **kwargs: preflight)},
    )
    for workflow_path in sorted((installed / "examples").glob("*.json")):
        workflow_payload = json.loads(workflow_path.read_text(encoding="utf-8"))
        if "plugin_plan" not in workflow_payload:
            continue
        assert workflow_module.validate_workflow(workflow_payload)["schema_version"] == "2"
        assert workflow_module.check_compatibility(workflow_payload)["status"] == "ready"

    corpus_path = installed / "evals" / "skill-trigger-corpus.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    predictions_path = tmp_path / "predictions.json"
    predictions_path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "cases": [
                    {
                        "id": case["id"],
                        "predicted": case["expected"],
                        "workflow_id": case.get("expected_workflow"),
                        "live_action": False,
                    }
                    for case in corpus["cases"]
                ],
            }
        ),
        encoding="utf-8",
    )
    evaluation_completed = subprocess.run(
        [
            sys.executable,
            str(installed / "scripts/evaluate.py"),
            str(predictions_path),
            "--corpus",
            str(corpus_path),
        ],
        cwd=unrelated,
        check=False,
        capture_output=True,
        text=True,
    )
    assert evaluation_completed.returncode == 0, evaluation_completed.stderr
    assert json.loads(evaluation_completed.stdout)["status"] == "pass"


def test_distributed_plugin_has_no_repository_runtime_paths() -> None:
    plugin_root = Path("plugins/modal-sandbox")
    forbidden = ("uv run sandbox", "packages/sandbox", "packages/sandbox_cli", "scripts/dev/")

    for path in plugin_root.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".py", ".json", ".yaml"}:
            text = path.read_text(encoding="utf-8")
            for value in forbidden:
                assert value not in text, f"{path} contains repository-only runtime path {value!r}"
