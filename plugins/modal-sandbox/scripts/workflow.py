#!/usr/bin/env python3
"""Validate, plan, or compatibility-check modal-sandbox plugin workflows."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

WORKFLOW_SCHEMA_VERSION = "2"
SUPPORTED_WORKFLOW_SCHEMA_VERSIONS = {"1", WORKFLOW_SCHEMA_VERSION}
REQUIRED_CLI_SCHEMA_VERSION = "1"
DEFAULT_MIN_CLI_VERSION = "0.4.1"
WORKFLOW_IDS = {
    "benchmark-two-approaches",
    "debug-failing-script",
    "filesystem-inspection",
    "inspect-and-cleanup",
    "persistent-workspace",
    "resource-controlled-job",
    "reusable-coding-sandbox",
    "run-tests-safely",
    "seed-and-test-project",
    "service-with-readiness",
}
SAFE_DISCOVERY_COMMANDS = {
    "sandbox doctor",
    "sandbox dry",
    "sandbox quickstart",
    "sandbox schema",
    "sandbox schema --agent",
}
DEFAULT_RECOVERY_GUIDANCE = {
    "invalid_arguments": "Correct the arguments and preview the command again.",
    "remote_nonzero": "Report the command result and inspect stderr before changing the workflow.",
    "timeout": "Report the timeout and increase a bound only when the user approves the tradeoff.",
    "truncated_output": "Report truncation and rerun with a larger output bound only when needed.",
    "readiness_failure": "Inspect the declared probe, service logs, and port before retrying.",
    "cleanup_failure": "Report the remaining resource identifier and the exact cleanup command.",
}


class WorkflowError(ValueError):
    """Raised when a plugin workflow contract is invalid."""


def _strings(value: object, name: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise WorkflowError(f"{name} must be an array")
    if not allow_empty and not value:
        raise WorkflowError(f"{name} must not be empty")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise WorkflowError(f"{name} must contain non-empty strings")
    return [item.strip() for item in value]


def _string_map(value: object, name: str) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise WorkflowError(f"{name} must be a non-empty object")
    if not all(isinstance(key, str) and key and isinstance(item, str) and item.strip() for key, item in value.items()):
        raise WorkflowError(f"{name} must map non-empty strings to non-empty strings")
    return {str(key): str(item).strip() for key, item in value.items()}


def _is_safe_discovery_command(command: str) -> bool:
    return command in SAFE_DISCOVERY_COMMANDS


def _is_resource_free_preview(command: str) -> bool:
    words = shlex.split(command)
    if words[:1] == ["sandbox"]:
        if words[1:2] == ["cleanup"] and "--yes" not in words:
            return True
        return "preview" in words
    return (
        len(words) >= 3
        and words[0] in {"python", "python3"}
        and words[1] == "<plugin-root>/scripts/benchmark.py"
        and "--validate-only" in words
        and "--allow-live" not in words
    )


def _command_capability(command: str) -> str | None:
    """Return the CLI capability exercised by a plugin command."""
    try:
        words = shlex.split(command)
    except ValueError:
        return None
    if not words or words[0] != "sandbox":
        return "benchmark" if "benchmark.py" in command else None
    if "preview" in words:
        index = words.index("preview")
        return words[index + 1] if index + 1 < len(words) else None
    for candidate in (
        "cleanup",
        "domain",
        "read",
        "run",
        "run-command",
        "seed-git",
        "seed-tarball",
        "snapshot",
        "snapshot-directory",
        "snapshot-filesystem",
        "start",
        "stat",
        "status",
        "stop",
        "sync",
        "wait-ready",
        "watch",
        "write",
    ):
        if candidate in words:
            return candidate
    return None


def _infer_capabilities(commands: list[str]) -> list[str]:
    return sorted({capability for command in commands if (capability := _command_capability(command))})


@dataclass(frozen=True)
class PluginPlan:
    """Validated resource boundary and lifecycle commands for one workflow."""

    required_cli_schema: str
    required_capabilities: list[str]
    safe_commands: list[str]
    preview_commands: list[str]
    live_commands: list[str]
    verification_commands: list[str]
    cleanup_commands: list[str]
    approval_points: list[str]
    expected_result_fields: list[str]
    recovery_guidance: dict[str, str]
    resource_boundary: str
    approval_required: bool = True

    @classmethod
    def from_payload(cls, payload: object, *, legacy: bool = False) -> PluginPlan:
        """Validate and build a plugin plan from workflow JSON data."""
        if not isinstance(payload, dict):
            raise WorkflowError("plugin_plan must be an object")

        safe_commands = _strings(payload.get("safe_commands"), "plugin_plan.safe_commands")
        if not all(_is_safe_discovery_command(command) for command in safe_commands):
            raise WorkflowError("plugin_plan.safe_commands contains a command outside safe discovery")

        if legacy:
            preview_value = payload.get("preview_command")
            preview_commands = [preview_value] if isinstance(preview_value, str) else []
        else:
            preview_commands = _strings(payload.get("preview_commands"), "plugin_plan.preview_commands")
        if not preview_commands or not all(_is_resource_free_preview(command) for command in preview_commands):
            raise WorkflowError("plugin_plan.preview_commands must contain only resource-free previews")

        live_commands = _strings(payload.get("live_commands"), "plugin_plan.live_commands", allow_empty=True)
        cleanup_commands = _strings(
            payload.get("cleanup_commands", []), "plugin_plan.cleanup_commands", allow_empty=True
        )
        verification_commands = _strings(
            payload.get("verification_commands", []),
            "plugin_plan.verification_commands",
            allow_empty=True,
        )
        if payload.get("approval_required") is not True:
            raise WorkflowError("plugin_plan.approval_required must be true")
        resource_boundary = payload.get("resource_boundary")
        if not isinstance(resource_boundary, str) or "explicit" not in resource_boundary.lower():
            raise WorkflowError("plugin_plan.resource_boundary must describe explicit approval")

        all_operational_commands = [
            *preview_commands,
            *live_commands,
            *verification_commands,
            *cleanup_commands,
        ]
        required_capabilities = (
            _infer_capabilities(all_operational_commands)
            if legacy
            else _strings(payload.get("required_capabilities"), "plugin_plan.required_capabilities")
        )
        required_cli_schema = REQUIRED_CLI_SCHEMA_VERSION if legacy else payload.get("required_cli_schema")
        if required_cli_schema != REQUIRED_CLI_SCHEMA_VERSION:
            raise WorkflowError(f"plugin_plan.required_cli_schema must be {REQUIRED_CLI_SCHEMA_VERSION!r}")
        approval_points = (
            ["before_live", "before_destructive_cleanup"]
            if legacy
            else _strings(payload.get("approval_points"), "plugin_plan.approval_points")
        )
        allowed_approval_points = {"before_live", "before_destructive_cleanup"}
        if not set(approval_points).issubset(allowed_approval_points):
            raise WorkflowError("plugin_plan.approval_points contains an unsupported boundary")
        expected_result_fields = (
            ["status"]
            if legacy
            else _strings(
                payload.get("expected_result_fields"),
                "plugin_plan.expected_result_fields",
            )
        )
        recovery_guidance = (
            dict(DEFAULT_RECOVERY_GUIDANCE)
            if legacy
            else _string_map(payload.get("recovery_guidance"), "plugin_plan.recovery_guidance")
        )

        declared = set(required_capabilities)
        inferred = set(_infer_capabilities(all_operational_commands))
        missing_declarations = inferred - declared - {"benchmark"}
        if missing_declarations:
            missing = ", ".join(sorted(missing_declarations))
            raise WorkflowError(f"plugin_plan.required_capabilities is missing: {missing}")

        return cls(
            required_cli_schema=str(required_cli_schema),
            required_capabilities=required_capabilities,
            safe_commands=safe_commands,
            preview_commands=preview_commands,
            live_commands=live_commands,
            verification_commands=verification_commands,
            cleanup_commands=cleanup_commands,
            approval_points=approval_points,
            expected_result_fields=expected_result_fields,
            recovery_guidance=recovery_guidance,
            resource_boundary=resource_boundary,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable workflow plan."""
        return {
            "required_cli_schema": self.required_cli_schema,
            "required_capabilities": self.required_capabilities,
            "safe_commands": self.safe_commands,
            "preview_commands": self.preview_commands,
            "live_commands": self.live_commands,
            "verification_commands": self.verification_commands,
            "cleanup_commands": self.cleanup_commands,
            "approval_required": self.approval_required,
            "approval_points": self.approval_points,
            "expected_result_fields": self.expected_result_fields,
            "recovery_guidance": self.recovery_guidance,
            "resource_boundary": self.resource_boundary,
        }


@dataclass(frozen=True)
class WorkflowExample:
    """Validated and normalized plugin workflow example."""

    id: str
    user_prompt: str
    plugin_plan: PluginPlan
    schema_version: str = WORKFLOW_SCHEMA_VERSION

    @classmethod
    def from_payload(cls, payload: object) -> WorkflowExample:
        """Validate a workflow and normalize supported versions to version 2."""
        if not isinstance(payload, dict):
            raise WorkflowError("workflow must be a JSON object")
        schema_version = payload.get("schema_version")
        if schema_version not in SUPPORTED_WORKFLOW_SCHEMA_VERSIONS:
            supported = ", ".join(sorted(SUPPORTED_WORKFLOW_SCHEMA_VERSIONS))
            raise WorkflowError(f"schema_version must be one of: {supported}")
        workflow_id = payload.get("id")
        if workflow_id not in WORKFLOW_IDS:
            raise WorkflowError(f"unsupported workflow id: {workflow_id!r}")
        prompt = payload.get("user_prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise WorkflowError("user_prompt must be a non-empty string")
        return cls(
            id=str(workflow_id),
            user_prompt=prompt.strip(),
            plugin_plan=PluginPlan.from_payload(
                payload.get("plugin_plan"),
                legacy=schema_version == "1",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the normalized version 2 workflow."""
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "user_prompt": self.user_prompt,
            "plugin_plan": self.plugin_plan.to_dict(),
        }


def validate_workflow(payload: object) -> dict[str, Any]:
    """Validate and normalize one plugin workflow example."""
    return WorkflowExample.from_payload(payload).to_dict()


def _base_plan(
    *,
    capabilities: list[str],
    preview: list[str],
    live: list[str],
    verify: list[str],
    cleanup: list[str],
    result_fields: list[str],
) -> dict[str, Any]:
    return {
        "required_cli_schema": REQUIRED_CLI_SCHEMA_VERSION,
        "required_capabilities": capabilities,
        "safe_commands": ["sandbox dry", "sandbox doctor", "sandbox schema --agent"],
        "preview_commands": preview,
        "live_commands": live,
        "verification_commands": verify,
        "cleanup_commands": cleanup,
        "approval_required": True,
        "approval_points": ["before_live", "before_destructive_cleanup"],
        "expected_result_fields": result_fields,
        "recovery_guidance": dict(DEFAULT_RECOVERY_GUIDANCE),
        "resource_boundary": "Live Modal commands and destructive cleanup require explicit user approval.",
    }


def plan_from_intent(intent: str, *, command: str | None = None) -> dict[str, Any]:
    """Build a resource-free version 2 starter plan for a named intent."""
    if intent not in WORKFLOW_IDS:
        raise WorkflowError(f"unsupported workflow id: {intent!r}")
    command = command or "python -m pytest"
    quoted_command = shlex.quote(command)
    common_cleanup = [
        "sandbox status",
        "sandbox cleanup --app modal-sandbox-sdk",
        "sandbox cleanup --app modal-sandbox-sdk --yes",
    ]
    plans: dict[str, dict[str, Any]] = {
        "run-tests-safely": {
            "user_prompt": "Run this test suite in an isolated Modal Sandbox.",
            "plan": _base_plan(
                capabilities=["run", "status", "cleanup"],
                preview=[f"sandbox preview run {quoted_command}"],
                live=[f"sandbox run {quoted_command}"],
                verify=[],
                cleanup=common_cleanup,
                result_fields=["exit_code", "stdout", "stderr", "timed_out"],
            ),
        },
        "debug-failing-script": {
            "user_prompt": "Debug this failing script in a clean sandbox.",
            "plan": _base_plan(
                capabilities=["run", "status", "cleanup"],
                preview=[f"sandbox preview run {quoted_command}"],
                live=[f"sandbox run {quoted_command}"],
                verify=[],
                cleanup=common_cleanup,
                result_fields=["exit_code", "stdout", "stderr", "timed_out"],
            ),
        },
        "persistent-workspace": {
            "user_prompt": "Persist and verify generated files across sandbox runs.",
            "plan": _base_plan(
                capabilities=["run", "stat", "sync", "snapshot", "status", "cleanup"],
                preview=[f"sandbox --workspace-volume work preview run {quoted_command}"],
                live=[f"sandbox --workspace-volume work run {quoted_command}"],
                verify=[
                    "sandbox --workspace-volume work stat .",
                    "sandbox --workspace-volume work sync",
                    "sandbox --workspace-volume work snapshot",
                ],
                cleanup=common_cleanup,
                result_fields=["exit_code", "stdout", "stderr", "volume_name"],
            ),
        },
        "reusable-coding-sandbox": {
            "user_prompt": "Start, verify, and stop a reusable sandbox.",
            "plan": _base_plan(
                capabilities=["start", "run", "stop", "status", "cleanup"],
                preview=["sandbox --name agent-workspace preview start"],
                live=[
                    "sandbox --name agent-workspace start",
                    'sandbox --sandbox-name agent-workspace run "python --version"',
                ],
                verify=["sandbox status"],
                cleanup=["sandbox --sandbox-name agent-workspace stop", *common_cleanup],
                result_fields=["sandbox_id", "sandbox_name", "status"],
            ),
        },
        "benchmark-two-approaches": {
            "user_prompt": "Benchmark equivalent approaches under the same sandbox controls.",
            "plan": _base_plan(
                capabilities=["benchmark", "status", "cleanup"],
                preview=["python <plugin-root>/scripts/benchmark.py scenario.json --validate-only"],
                live=["python <plugin-root>/scripts/benchmark.py scenario.json --allow-live"],
                verify=[],
                cleanup=common_cleanup,
                result_fields=["status", "scenarios"],
            ),
        },
        "inspect-and-cleanup": {
            "user_prompt": "Inspect and clean up reusable sandbox resources.",
            "plan": _base_plan(
                capabilities=["cleanup", "status"],
                preview=["sandbox cleanup --app modal-sandbox-sdk"],
                live=["sandbox cleanup --app modal-sandbox-sdk --yes"],
                verify=["sandbox status"],
                cleanup=[],
                result_fields=["status", "results"],
            ),
        },
        "seed-and-test-project": {
            "user_prompt": "Seed a public project into a persistent workspace and test it.",
            "plan": _base_plan(
                capabilities=["seed-git", "run", "stat", "sync", "status", "cleanup"],
                preview=[
                    "sandbox --workspace-volume project preview seed-git https://github.com/example/project.git --dest src",
                    'sandbox --workspace-volume project preview run "python -m pytest src"',
                ],
                live=[
                    "sandbox --workspace-volume project seed-git https://github.com/example/project.git --dest src",
                    'sandbox --workspace-volume project run "python -m pytest src"',
                ],
                verify=[
                    "sandbox --workspace-volume project stat src",
                    "sandbox --workspace-volume project sync",
                ],
                cleanup=common_cleanup,
                result_fields=["exit_code", "stdout", "stderr", "timed_out"],
            ),
        },
        "service-with-readiness": {
            "user_prompt": "Start a service, wait for readiness, resolve its URL, and stop it.",
            "plan": _base_plan(
                capabilities=["start", "wait-ready", "domain", "stop", "status", "cleanup"],
                preview=["sandbox --name agent-service --encrypted-port 3000 --readiness-tcp 3000 preview start"],
                live=["sandbox --name agent-service --encrypted-port 3000 --readiness-tcp 3000 --wait-ready start"],
                verify=[
                    "sandbox --sandbox-name agent-service wait-ready --timeout 60",
                    "sandbox --sandbox-name agent-service domain 3000",
                ],
                cleanup=["sandbox --sandbox-name agent-service stop", *common_cleanup],
                result_fields=["sandbox_id", "sandbox_name", "ready", "url"],
            ),
        },
        "resource-controlled-job": {
            "user_prompt": "Run a job with declared compute and network controls.",
            "plan": _base_plan(
                capabilities=["run", "status", "cleanup"],
                preview=['sandbox --cpu 1 --memory 1024 --block-network preview run "python job.py"'],
                live=['sandbox --cpu 1 --memory 1024 --block-network run "python job.py"'],
                verify=[],
                cleanup=common_cleanup,
                result_fields=["exit_code", "stdout", "stderr", "timed_out"],
            ),
        },
        "filesystem-inspection": {
            "user_prompt": "Inspect, watch, sync, and snapshot a persistent workspace.",
            "plan": _base_plan(
                capabilities=[
                    "stat",
                    "watch",
                    "sync",
                    "snapshot",
                    "snapshot-filesystem",
                    "status",
                    "cleanup",
                ],
                preview=["sandbox --workspace-volume work preview stat ."],
                live=[
                    "sandbox --workspace-volume work stat .",
                    "sandbox --workspace-volume work watch . --timeout 5 --recursive",
                    "sandbox --workspace-volume work sync",
                    "sandbox --workspace-volume work snapshot",
                    "sandbox --workspace-volume work snapshot-filesystem --ttl 604800",
                ],
                verify=["sandbox --workspace-volume work stat ."],
                cleanup=common_cleanup,
                result_fields=["path", "events", "volume_name", "image_id"],
            ),
        },
    }
    selected = plans[intent]
    return validate_workflow(
        {
            "schema_version": WORKFLOW_SCHEMA_VERSION,
            "id": intent,
            "user_prompt": selected["user_prompt"],
            "plugin_plan": selected["plan"],
        }
    )


def _load_preflight_module() -> ModuleType:
    try:
        import preflight

        return preflight
    except ImportError as exc:
        path = Path(__file__).with_name("preflight.py")
        spec = importlib.util.spec_from_file_location("modal_sandbox_plugin_preflight", path)
        if spec is None or spec.loader is None:
            raise WorkflowError("could not load the distributed preflight helper") from exc
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


def _available_capabilities(agent_schema: object) -> set[str]:
    if not isinstance(agent_schema, dict):
        return set()
    capabilities: set[str] = set()
    live = agent_schema.get("live_modal")
    if isinstance(live, dict):
        commands = live.get("commands")
        if isinstance(commands, list):
            capabilities.update(str(command) for command in commands if isinstance(command, str))
    resources = agent_schema.get("resource_management")
    if isinstance(resources, dict):
        if resources.get("status_command"):
            capabilities.add("status")
        if resources.get("cleanup_preview"):
            capabilities.add("cleanup")
    return capabilities


def check_compatibility(
    workflow: dict[str, Any],
    *,
    executable: str = "sandbox",
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Check workflow requirements using only resource-free CLI operations."""
    normalized = validate_workflow(workflow)
    preflight = _load_preflight_module().run_preflight(
        executable,
        min_version=DEFAULT_MIN_CLI_VERSION,
        timeout_seconds=timeout_seconds,
    )
    result: dict[str, Any] = {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "resource_free": True,
        "workflow_id": normalized["id"],
        "required_cli_schema": normalized["plugin_plan"]["required_cli_schema"],
        "required_capabilities": normalized["plugin_plan"]["required_capabilities"],
        "preflight": preflight,
    }
    if not preflight.get("ok"):
        error = preflight.get("error", {})
        code = error.get("code") if isinstance(error, dict) else None
        result.update(
            {
                "status": (
                    "incompatible"
                    if code in {"cli_outdated", "incompatible_cli_schema", "invalid_cli_version"}
                    else "blocked"
                ),
                "ready_for_live": False,
                "missing_capabilities": [],
                "next_action": "fix_cli_compatibility" if code else "fix_preflight_error",
            }
        )
        return result

    checks = preflight.get("checks")
    schema = checks.get("schema") if isinstance(checks, dict) else None
    available = _available_capabilities(schema)
    required = set(normalized["plugin_plan"]["required_capabilities"])
    missing = sorted(required - available - {"benchmark"})
    if missing:
        result.update(
            {
                "status": "incompatible",
                "ready_for_live": False,
                "missing_capabilities": missing,
                "next_action": "upgrade_cli",
            }
        )
    elif not preflight.get("ready_for_live"):
        result.update(
            {
                "status": "blocked",
                "ready_for_live": False,
                "missing_capabilities": [],
                "next_action": "complete_modal_setup",
            }
        )
    else:
        result.update(
            {
                "status": "ready",
                "ready_for_live": True,
                "missing_capabilities": [],
                "next_action": "request_live_approval",
            }
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", nargs="?", type=Path)
    parser.add_argument("--intent", choices=sorted(WORKFLOW_IDS))
    parser.add_argument("--command")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--check-compatibility", action="store_true")
    parser.add_argument(
        "--sandbox-executable",
        default=os.environ.get("MODAL_SANDBOX_CLI", "sandbox"),
    )
    parser.add_argument("--timeout", type=int, default=30, dest="timeout_seconds")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.timeout_seconds <= 0:
            raise WorkflowError("--timeout must be greater than zero")
        if args.workflow is not None:
            payload = json.loads(args.workflow.read_text(encoding="utf-8"))
            workflow = validate_workflow(payload)
        elif args.intent:
            workflow = plan_from_intent(args.intent, command=args.command)
        else:
            raise WorkflowError("provide a workflow file or --intent")
        if args.check_compatibility:
            result = check_compatibility(
                workflow,
                executable=args.sandbox_executable,
                timeout_seconds=args.timeout_seconds,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] == "ready" else 1
    except (OSError, json.JSONDecodeError, WorkflowError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": WORKFLOW_SCHEMA_VERSION,
                    "status": "invalid_workflow",
                    "resource_free": True,
                    "error": {"message": str(exc)},
                }
            )
        )
        return 2

    if args.validate_only:
        print(
            json.dumps(
                {
                    "schema_version": WORKFLOW_SCHEMA_VERSION,
                    "status": "valid",
                    "resource_free": True,
                    "id": workflow["id"],
                }
            )
        )
    else:
        print(
            json.dumps(
                {
                    "schema_version": WORKFLOW_SCHEMA_VERSION,
                    "status": "planned",
                    "resource_free": True,
                    "workflow": workflow,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
