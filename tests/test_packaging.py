from __future__ import annotations

import tomllib
from pathlib import Path


def test_project_metadata_matches_sandbox_harness_identity() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["name"] == "modal-agent-sandbox"
    assert data["project"]["requires-python"] == ">=3.11"
    assert data["project"]["scripts"] == {
        "sandbox-harness": "modal_agent_sandbox.cli:main",
    }
    assert data["dependency-groups"]["dev"] == ["pytest>=8.0"]


def test_python_version_file_pins_local_development_runtime() -> None:
    assert Path(".python-version").read_text(encoding="utf-8").strip() == "3.13"
