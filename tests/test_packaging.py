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
    assert hasattr(sdk, "ModalAuthenticationError")
    assert hasattr(sdk, "SandboxConfig")
    assert hasattr(sdk, "Images")


def test_image_presets_are_registry_tags() -> None:
    from sandbox import Images

    assert Images.PY313 == "python:3.13-slim"
    assert Images.PY312 == "python:3.12-slim"
    assert Images.PY311 == "python:3.11-slim"
    assert Images.UBUNTU24 == "ubuntu:24.04"
    assert Images.PYTHON_313_SLIM == "python:3.13-slim"
    assert Images.PYTHON_312_SLIM == "python:3.12-slim"
    assert Images.PYTHON_311_SLIM == "python:3.11-slim"
    assert Images.UBUNTU_2404 == "ubuntu:24.04"


def test_python_version_file_pins_local_development_runtime() -> None:
    assert Path(".python-version").read_text(encoding="utf-8").strip() == "3.13"


def test_beginner_examples_are_present() -> None:
    examples = Path("examples")

    assert (examples / "run_python.py").read_text(encoding="utf-8")
    assert (examples / "cli_file_workflow.sh").read_text(encoding="utf-8").startswith("#!/usr/bin/env sh")
    assert (examples / "persistent_volume.sh").read_text(encoding="utf-8").startswith("#!/usr/bin/env sh")


def test_repo_local_skills_are_model_neutral_source_artifacts() -> None:
    expected_skills = {
        "modal-sandbox-first-run",
        "modal-sandbox-cli-workflows",
        "modal-sandbox-file-workflows",
        "modal-sandbox-python-sdk",
    }
    skills_root = Path("skills")
    skill_dirs = {path.name for path in skills_root.iterdir() if path.is_dir()}

    assert skill_dirs == expected_skills

    for skill_name in expected_skills:
        skill_dir = skills_root / skill_name
        skill_file = skill_dir / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        frontmatter = content.split("---", 2)[1].strip()
        metadata = dict(line.split(": ", 1) for line in frontmatter.splitlines())

        assert set(metadata) == {"name", "description"}
        assert metadata["name"] == skill_name
        assert metadata["description"]
        assert not (skill_dir / "agents" / "openai.yaml").exists()
