from __future__ import annotations

import importlib
import tomllib
from pathlib import Path


def test_project_metadata_matches_modal_sandbox_sdk_identity() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["name"] == "modal-sandbox-sdk"
    assert data["project"]["requires-python"] == ">=3.11"
    assert data["project"]["license"] == "MIT"
    assert data["project"]["authors"] == [{"name": "DaleGrinter1", "email": "dalegrinter1@gmail.com"}]
    assert "License :: OSI Approved :: MIT License" in data["project"]["classifiers"]
    assert data["project"]["urls"]["Repository"] == "https://github.com/DaleGrinter1/sandbox-harness"
    assert data["project"]["dependencies"] == ["modal>=1.5.0"]
    assert data["project"]["scripts"] == {
        "sandbox": "sandbox_cli.cli:main",
    }
    assert data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "packages/sandbox",
        "packages/sandbox_cli",
    ]
    assert data["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"] == {
        "packages/sandbox/py.typed": "sandbox/py.typed",
    }
    assert data["dependency-groups"]["dev"] == [
        "pre-commit>=4.0",
        "pyright>=1.1.407",
        "pytest>=8.0",
        "ruff>=0.14.0",
    ]
    assert data["tool"]["ruff"]["line-length"] == 120
    assert data["tool"]["pyright"]["typeCheckingMode"] == "basic"


def test_public_imports_are_available() -> None:
    sdk = importlib.import_module("sandbox")
    commands = importlib.import_module("sandbox.commands")
    errors = importlib.import_module("sandbox.errors")
    files = importlib.import_module("sandbox.files")
    volumes = importlib.import_module("sandbox.volumes")

    assert hasattr(sdk, "Sandbox")
    assert hasattr(sdk, "CommandResult")
    assert hasattr(sdk, "ModalAuthenticationError")
    assert hasattr(sdk, "RuntimeSpec")
    assert hasattr(sdk, "SandboxCommand")
    assert hasattr(sdk, "SandboxConfigurationError")
    assert hasattr(sdk, "SandboxConfig")
    assert hasattr(sdk, "SandboxError")
    assert hasattr(sdk, "SandboxFile")
    assert hasattr(sdk, "SandboxProviderError")
    assert hasattr(sdk, "SandboxSnapshot")
    assert hasattr(sdk, "SandboxVolume")
    assert hasattr(sdk, "Images")
    assert sdk.CommandResult is commands.CommandResult
    assert sdk.SandboxCommand is commands.SandboxCommand
    assert sdk.ModalAuthenticationError is errors.ModalAuthenticationError
    assert sdk.SandboxConfigurationError is errors.SandboxConfigurationError
    assert sdk.SandboxError is errors.SandboxError
    assert sdk.SandboxProviderError is errors.SandboxProviderError
    assert sdk.SandboxFile is files.SandboxFile
    assert sdk.SandboxVolume is volumes.SandboxVolume
    assert hasattr(volumes, "VolumeSpec")


def test_license_file_is_present() -> None:
    license_text = Path("LICENSE").read_text(encoding="utf-8")

    assert license_text.startswith("MIT License")
    assert "Copyright (c) 2026 Dale" in license_text


def test_image_presets_are_registry_tags() -> None:
    from sandbox import Images

    assert Images.PY313 == "python:3.13-slim"
    assert Images.PY312 == "python:3.12-slim"
    assert Images.PY311 == "python:3.11-slim"
    assert Images.UBUNTU24 == "ubuntu:24.04"


def test_python_version_file_pins_local_development_runtime() -> None:
    assert Path(".python-version").read_text(encoding="utf-8").strip() == "3.13"


def test_package_marks_inline_types() -> None:
    assert Path("packages/sandbox/py.typed").exists()


def test_beginner_examples_are_present() -> None:
    examples = Path("examples")

    assert (examples / "run_python.py").read_text(encoding="utf-8")
    assert (examples / "argv_command.py").read_text(encoding="utf-8")
    assert (examples / "node_dev_server.py").read_text(encoding="utf-8")
    assert (examples / "reuse_sandbox.py").read_text(encoding="utf-8")
    assert (examples / "volume_mounts.py").read_text(encoding="utf-8")
    assert (examples / "cli_file_workflow.sh").read_text(encoding="utf-8").startswith("#!/usr/bin/env sh")
    assert (examples / "persistent_volume.sh").read_text(encoding="utf-8").startswith("#!/usr/bin/env sh")


def test_repo_local_agent_skills_are_development_only_source_artifacts() -> None:
    expected_skills = {
        "modal-sandbox-cli-workflows",
        "modal-sandbox-package-maintenance",
        "modal-sandbox-repo-understanding",
        "modal-sandbox-understanding-check",
    }
    codex_root = Path(".codex")
    skills_root = Path(".agents") / "skills"

    assert (codex_root / "config.toml").read_text(encoding="utf-8")
    assert (codex_root / "README.md").read_text(encoding="utf-8")
    assert not (codex_root / "skills").exists()

    skill_dirs = {path.name for path in skills_root.iterdir() if path.is_dir()}

    assert expected_skills <= skill_dirs
    assert skill_dirs - expected_skills <= {"modal"}

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
