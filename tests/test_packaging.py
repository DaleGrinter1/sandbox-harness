from __future__ import annotations

import importlib
import importlib.util
import json
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
    assert data["project"]["dependencies"] == ["modal>=1.5,<2", "pydantic>=2,<3"]
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
        "twine>=6.2.0",
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
    assert hasattr(sdk, "ReadinessProbeSpec")
    assert hasattr(sdk, "RuntimeSpec")
    assert hasattr(sdk, "SandboxCommand")
    assert hasattr(sdk, "SandboxConflictError")
    assert hasattr(sdk, "SandboxConfigurationError")
    assert hasattr(sdk, "SandboxConfig")
    assert hasattr(sdk, "SandboxError")
    assert hasattr(sdk, "SandboxFile")
    assert hasattr(sdk, "SandboxFileStat")
    assert hasattr(sdk, "SandboxFilesystemError")
    assert hasattr(sdk, "SandboxImageSnapshot")
    assert hasattr(sdk, "SandboxReadinessProbe")
    assert hasattr(sdk, "SandboxNotFoundError")
    assert hasattr(sdk, "SandboxPermissionError")
    assert hasattr(sdk, "SandboxProviderError")
    assert hasattr(sdk, "SandboxSnapshot")
    assert hasattr(sdk, "SandboxTimeoutError")
    assert hasattr(sdk, "SandboxVolume")
    assert hasattr(sdk, "SandboxWatchEvent")
    assert hasattr(sdk, "Images")
    assert sdk.CommandResult is commands.CommandResult
    assert sdk.SandboxCommand is commands.SandboxCommand
    assert sdk.ModalAuthenticationError is errors.ModalAuthenticationError
    assert sdk.SandboxConflictError is errors.SandboxConflictError
    assert sdk.SandboxConfigurationError is errors.SandboxConfigurationError
    assert sdk.SandboxError is errors.SandboxError
    assert sdk.SandboxFilesystemError is errors.SandboxFilesystemError
    assert sdk.SandboxNotFoundError is errors.SandboxNotFoundError
    assert sdk.SandboxPermissionError is errors.SandboxPermissionError
    assert sdk.SandboxProviderError is errors.SandboxProviderError
    assert sdk.SandboxTimeoutError is errors.SandboxTimeoutError
    assert sdk.SandboxFile is files.SandboxFile
    assert sdk.SandboxFileStat.__name__ == "SandboxFileStat"
    assert sdk.SandboxImageSnapshot.__name__ == "SandboxImageSnapshot"
    assert sdk.SandboxReadinessProbe.__name__ == "SandboxReadinessProbe"
    assert sdk.SandboxWatchEvent.__name__ == "SandboxWatchEvent"
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


def test_release_readiness_files_are_present() -> None:
    pre_commit = Path(".pre-commit-config.yaml").read_text(encoding="utf-8")
    release_check = Path("scripts/dev/release-check.sh").read_text(encoding="utf-8")
    publish_workflow = Path(".github/workflows/publish.yml").read_text(encoding="utf-8")
    testpypi_workflow = Path(".github/workflows/testpypi.yml").read_text(encoding="utf-8")

    assert "stages: [pre-push]" in pre_commit
    assert "id: release-check" in pre_commit
    assert "uv build" in release_check
    assert "twine check dist/*" in release_check
    assert "id-token: write" in publish_workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in publish_workflow
    assert "repository-url: https://test.pypi.org/legacy/" in testpypi_workflow


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


def test_modal_sandbox_plugin_identity_and_marketplace_contract() -> None:
    plugin_root = Path("plugins/modal-sandbox")
    manifest = json.loads((plugin_root / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    marketplace = json.loads(Path(".agents/plugins/marketplace.json").read_text(encoding="utf-8"))

    assert manifest["name"] == plugin_root.name == "modal-sandbox"
    assert manifest["version"] == "0.1.0"
    assert manifest["license"] == "MIT"
    assert manifest["repository"] == "https://github.com/DaleGrinter1/sandbox-harness"
    assert manifest["skills"] == "./skills/"
    assert manifest["interface"]["category"] == "Developer Tools"
    assert "mcpServers" not in manifest
    assert "apps" not in manifest
    assert "hooks" not in manifest

    assert marketplace["name"] == "personal"
    assert marketplace["interface"]["displayName"] == "Personal"
    assert marketplace["plugins"] == [
        {
            "name": "modal-sandbox",
            "source": {"source": "local", "path": "./plugins/modal-sandbox"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Developer Tools",
        }
    ]


def test_public_skill_encodes_cli_prerequisite_and_safe_workflows() -> None:
    skill_root = Path("plugins/modal-sandbox/skills/modal-sandbox")
    skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    openai_yaml = (skill_root / "agents/openai.yaml").read_text(encoding="utf-8")

    frontmatter = skill.split("---", 2)[1].strip()
    assert frontmatter.startswith("name: modal-sandbox\n")
    assert "execute code or tests in isolation" in frontmatter
    assert "pip install modal-sandbox-sdk" in skill
    assert "Do not install the package silently" in skill
    assert "sandbox dry" in skill
    assert "sandbox doctor" in skill
    assert "sandbox schema --agent" in skill
    assert "doctor.credentials.authenticated" in skill
    assert "Use `sandbox run` or `sandbox run-command`" in skill
    assert "--workspace-volume NAME" in skill
    assert "--name NAME start" in skill
    assert "Stop an agent-created reusable" in skill
    assert "A nonzero sandbox command exit is a" in skill
    assert "Discovery, explanation, and planning requests do not" in skill
    assert 'default_prompt: "Use $modal-sandbox' in openai_yaml


def test_plugin_docs_record_schema_compatibility_and_new_thread_install_flow() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    development = Path("docs/references/development.md").read_text(encoding="utf-8")

    assert "pip install modal-sandbox-sdk" in readme
    assert "codex plugin marketplace add .agents/plugins" in readme
    assert "codex plugin add modal-sandbox@personal" in readme
    assert "Start a new Codex thread" in readme
    assert "plugin `0.1.x` is tested against CLI schema version `1`" in development
    assert "update-plugin-cachebuster.py" in development


def test_plugin_cachebuster_replaces_existing_suffix() -> None:
    script_path = Path("scripts/dev/update-plugin-cachebuster.py")
    spec = importlib.util.spec_from_file_location("update_plugin_cachebuster", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.with_cachebuster("0.1.0", "Local Test") == "0.1.0+codex.local-test"
    assert module.with_cachebuster("0.1.0+codex.old", "next") == "0.1.0+codex.next"
