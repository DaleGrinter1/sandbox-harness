from __future__ import annotations

import importlib
import tomllib
from pathlib import Path


def test_project_metadata_matches_modal_sandbox_sdk_identity() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["name"] == "modal-sandbox-sdk"
    assert data["project"]["requires-python"] == ">=3.11"
    assert data["project"]["dependencies"] == ["modal>=1.4.3"]
    assert data["project"]["scripts"] == {
        "sandbox": "sandbox_cli.cli:main",
    }
    assert data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "packages/sandbox",
        "packages/sandbox_cli",
    ]
    assert data["dependency-groups"]["dev"] == ["pytest>=8.0"]


def test_public_imports_are_available() -> None:
    sdk = importlib.import_module("sandbox")

    assert hasattr(sdk, "Sandbox")
    assert hasattr(sdk, "CommandResult")
    assert hasattr(sdk, "SandboxConfig")


def test_python_version_file_pins_local_development_runtime() -> None:
    assert Path(".python-version").read_text(encoding="utf-8").strip() == "3.13"
