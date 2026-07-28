from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

PLUGIN_ROOT = Path(__file__).parents[1] / "plugins" / "modal-sandbox"
SCRIPTS_ROOT = PLUGIN_ROOT / "scripts"
EXAMPLE_MANIFEST = PLUGIN_ROOT / "examples" / "python-json-workflow.json"


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def preflight_module() -> ModuleType:
    return _load_module("modal_sandbox_plugin_preflight", SCRIPTS_ROOT / "preflight.py")


@pytest.fixture
def benchmark_module(preflight_module: ModuleType, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.setitem(sys.modules, "preflight", preflight_module)
    return _load_module("modal_sandbox_plugin_benchmark", SCRIPTS_ROOT / "benchmark.py")


@pytest.fixture
def workflow_module() -> ModuleType:
    return _load_module("modal_sandbox_plugin_workflow", SCRIPTS_ROOT / "workflow.py")


def _completed(
    arguments: list[str], payload: dict[str, Any] | None = None, *, stdout: str = ""
) -> subprocess.CompletedProcess[str]:
    if payload is not None:
        stdout = json.dumps(payload)
    return subprocess.CompletedProcess(arguments, 0, stdout=stdout, stderr="")


def test_preflight_runs_only_resource_free_commands(
    preflight_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[-1] == "--version":
            return _completed(command, stdout="sandbox 0.4.0\n")
        if command[-1] == "doctor":
            return _completed(command, {"credentials": {"complete": True, "verified": False}})
        if command[-2:] == ["schema", "--agent"]:
            return _completed(command, {"schema_version": "1", "golden_workflows": []})
        return _completed(command, {"creates_modal_resources": False})

    monkeypatch.setattr(preflight_module.subprocess, "run", fake_run)
    result = preflight_module.run_preflight("fake-sandbox")

    assert result["ok"] is True
    assert result["resource_free"] is True
    assert result["ready_for_live"] is True
    assert result["summary"]["status"] == "ready_for_live"
    assert result["summary"]["safe_to_continue"] is True
    assert result["summary"]["next_action"] == "preview_live_command"
    assert result["summary"]["requires_user_approval"] is True
    assert result["checks"]["preview"]["creates_modal_resources"] is False
    assert calls == [
        ["fake-sandbox", "--version"],
        ["fake-sandbox", "dry"],
        ["fake-sandbox", "doctor"],
        ["fake-sandbox", "schema", "--agent"],
        ["fake-sandbox", "quickstart"],
        ["fake-sandbox", "--image", "py313", "preview", "run", "python", "-c", "print(123)"],
    ]


@pytest.mark.parametrize(
    ("version", "schema_version", "error_code"),
    [
        ("0.3.9", "1", "cli_outdated"),
        ("0.4.0", "2", "incompatible_cli_schema"),
    ],
)
def test_preflight_rejects_incompatible_cli(
    preflight_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    version: str,
    schema_version: str,
    error_code: str,
) -> None:
    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        if command[-1] == "--version":
            return _completed(command, stdout=f"sandbox {version}\n")
        if command[-1] == "doctor":
            return _completed(command, {"credentials": {"complete": False, "verified": False}})
        if command[-2:] == ["schema", "--agent"]:
            return _completed(command, {"schema_version": schema_version})
        return _completed(command, {})

    monkeypatch.setattr(preflight_module.subprocess, "run", fake_run)
    result = preflight_module.run_preflight("fake-sandbox")

    assert result["ok"] is False
    assert result["error"]["code"] == error_code


def test_preflight_rejects_malformed_cli_json(preflight_module: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        if command[-1] == "--version":
            return _completed(command, stdout="sandbox 0.4.0\n")
        return _completed(command, stdout="not-json")

    monkeypatch.setattr(preflight_module.subprocess, "run", fake_run)
    result = preflight_module.run_preflight("fake-sandbox")

    assert result["ok"] is False
    assert result["error"]["code"] == "invalid_cli_json"


def test_example_benchmark_manifest_validates_without_cli_from_unrelated_directory(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS_ROOT / "benchmark.py"), str(EXAMPLE_MANIFEST), "--validate-only"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload == {
        "schema_version": "1",
        "status": "valid",
        "resource_free": True,
        "benchmark_id": "python-json-workflow",
        "scenario_count": 1,
    }


def test_workflow_examples_validate_without_modal(workflow_module: ModuleType) -> None:
    for path in sorted((PLUGIN_ROOT / "examples").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "plugin_plan" not in payload:
            continue
        workflow = workflow_module.validate_workflow(payload)
        assert workflow["plugin_plan"]["approval_required"] is True
        assert workflow["plugin_plan"]["preview_command"]


def test_workflow_planner_emits_resource_free_plan(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_ROOT / "workflow.py"),
            "--intent",
            "run-tests-safely",
            "--command",
            "python -m pytest",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "planned"
    assert payload["resource_free"] is True
    assert payload["workflow"]["plugin_plan"]["approval_required"] is True


def test_benchmark_requires_explicit_live_authorization(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS_ROOT / "benchmark.py"), str(EXAMPLE_MANIFEST)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["status"] == "live_authorization_required"
    assert payload["resource_free"] is True


def test_manifest_validation_rejects_unbounded_and_conflicting_inputs(benchmark_module: ModuleType) -> None:
    payload = json.loads(EXAMPLE_MANIFEST.read_text(encoding="utf-8"))
    scenario = payload["scenarios"][0]
    scenario["repetitions"] = 21
    with pytest.raises(benchmark_module.ManifestError, match="repetitions"):
        benchmark_module.validate_manifest(payload)

    scenario["repetitions"] = 1
    scenario["network"] = {"block": True, "allow_domains": ["example.com"], "allow_cidrs": []}
    with pytest.raises(benchmark_module.ManifestError, match="cannot be combined"):
        benchmark_module.validate_manifest(payload)


@pytest.mark.parametrize(
    ("cli_payload", "returncode", "expected_failure"),
    [
        ({"exit_code": 0, "stdout": "ok", "stderr": "", "timed_out": False}, 0, None),
        ({"exit_code": 7, "stdout": "", "stderr": "failed", "timed_out": False}, 0, "remote_nonzero"),
        ({"exit_code": 124, "stdout": "", "stderr": "", "timed_out": True}, 0, "timeout"),
        (
            {
                "exit_code": 125,
                "stdout": "",
                "stderr": "modal-sandbox-benchmark-cleanup-failed",
                "timed_out": False,
            },
            0,
            "cleanup",
        ),
        ({"error": {"code": "provider_error"}}, 1, "cli_transport"),
    ],
)
def test_benchmark_classifies_results_and_redacts_output(
    benchmark_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    cli_payload: dict[str, Any],
    returncode: int,
    expected_failure: str | None,
) -> None:
    manifest = benchmark_module.validate_manifest(json.loads(EXAMPLE_MANIFEST.read_text(encoding="utf-8")))
    scenario = manifest["scenarios"][0]
    scenario["redact"] = ["secret"]
    cli_payload["stdout"] = f"{cli_payload.get('stdout', '')} secret"

    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, returncode, stdout=json.dumps(cli_payload), stderr="")

    monkeypatch.setattr(benchmark_module.subprocess, "run", fake_run)
    result = benchmark_module._run_once("fake-sandbox", scenario, 1)

    assert result["failure_class"] == expected_failure
    assert "secret" not in result.get("stdout_preview", "")
    assert "[REDACTED]" in result.get("stdout_preview", "")


def test_benchmark_retains_malformed_json_failure(
    benchmark_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = benchmark_module.validate_manifest(json.loads(EXAMPLE_MANIFEST.read_text(encoding="utf-8")))

    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="not json", stderr="")

    monkeypatch.setattr(benchmark_module.subprocess, "run", fake_run)
    result = benchmark_module._run_once("fake-sandbox", manifest["scenarios"][0], 1)

    assert result["failure_class"] == "malformed_cli_json"
    assert result["error"] == "not json"


def test_benchmark_retains_partial_runs(benchmark_module: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = benchmark_module.validate_manifest(json.loads(EXAMPLE_MANIFEST.read_text(encoding="utf-8")))
    manifest["scenarios"][0]["repetitions"] = 2
    monkeypatch.setattr(
        benchmark_module,
        "run_preflight",
        lambda _: {
            "ok": True,
            "ready_for_live": True,
            "cli": {"version": "0.4.0", "schema_version": "1"},
        },
    )
    responses = iter(
        [
            {"status": "preview", "creates_modal_resources": False},
            {"exit_code": 0, "stdout": "ok", "stderr": "", "timed_out": False},
            {"exit_code": 3, "stdout": "", "stderr": "failed", "timed_out": False},
        ]
    )

    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(next(responses)), stderr="")

    monkeypatch.setattr(benchmark_module.subprocess, "run", fake_run)
    result = benchmark_module.run_benchmark(manifest, "fake-sandbox")

    assert result["status"] == "completed_with_failures"
    assert result["scenarios"][0]["preview"]["payload"]["status"] == "preview"
    assert len(result["scenarios"][0]["runs"]) == 2
    assert result["scenarios"][0]["summary"]["successful_runs"] == 1


def test_benchmark_stops_when_authentication_is_unavailable(
    benchmark_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = benchmark_module.validate_manifest(json.loads(EXAMPLE_MANIFEST.read_text(encoding="utf-8")))
    monkeypatch.setattr(
        benchmark_module,
        "run_preflight",
        lambda _: {
            "ok": True,
            "credential_complete": False,
            "ready_for_live": False,
        },
    )

    result = benchmark_module.run_benchmark(manifest, "fake-sandbox")

    assert result["status"] == "preflight_failed"
    assert result["scenarios"] == []
