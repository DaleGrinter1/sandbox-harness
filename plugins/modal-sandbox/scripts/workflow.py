#!/usr/bin/env python3
"""Validate or emit resource-free modal-sandbox plugin workflow plans."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKFLOW_IDS = {
    "run-tests-safely",
    "debug-failing-script",
    "persistent-workspace",
    "reusable-coding-sandbox",
    "benchmark-two-approaches",
    "inspect-and-cleanup",
}


class WorkflowError(ValueError):
    pass


@dataclass(frozen=True)
class PluginPlan:
    """Resource boundary and commands for one plugin workflow."""

    safe_commands: list[str]
    preview_command: str
    live_commands: list[str]
    cleanup_commands: list[str]
    approval_required: bool
    resource_boundary: str

    @classmethod
    def from_payload(cls, payload: object) -> PluginPlan:
        """Validate and build a plugin plan from JSON data."""
        if not isinstance(payload, dict):
            raise WorkflowError("plugin_plan must be an object")

        safe_commands = _strings(payload.get("safe_commands"), "plugin_plan.safe_commands")
        preview_command = payload.get("preview_command")
        if not isinstance(preview_command, str) or not _is_resource_free_preview(preview_command):
            raise WorkflowError("plugin_plan.preview_command must be a resource-free preview command")
        live_commands = _strings(payload.get("live_commands"), "plugin_plan.live_commands", allow_empty=True)
        cleanup_commands = _strings(
            payload.get("cleanup_commands", []), "plugin_plan.cleanup_commands", allow_empty=True
        )
        approval_required = payload.get("approval_required")
        if approval_required is not True:
            raise WorkflowError("plugin_plan.approval_required must be true")
        resource_boundary = payload.get("resource_boundary")
        if not isinstance(resource_boundary, str) or "explicit" not in resource_boundary.lower():
            raise WorkflowError("plugin_plan.resource_boundary must describe explicit approval")

        return cls(
            safe_commands=safe_commands,
            preview_command=preview_command,
            live_commands=live_commands,
            cleanup_commands=cleanup_commands,
            approval_required=approval_required,
            resource_boundary=resource_boundary,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable plan."""
        return {
            "safe_commands": self.safe_commands,
            "preview_command": self.preview_command,
            "live_commands": self.live_commands,
            "cleanup_commands": self.cleanup_commands,
            "approval_required": self.approval_required,
            "resource_boundary": self.resource_boundary,
        }


@dataclass(frozen=True)
class WorkflowExample:
    """Validated plugin workflow example."""

    id: str
    user_prompt: str
    plugin_plan: PluginPlan
    schema_version: str = "1"

    @classmethod
    def from_payload(cls, payload: object) -> WorkflowExample:
        """Validate and build a workflow example from JSON data."""
        if not isinstance(payload, dict):
            raise WorkflowError("workflow must be a JSON object")
        if payload.get("schema_version") != "1":
            raise WorkflowError('schema_version must be "1"')
        workflow_id = payload.get("id")
        if workflow_id not in WORKFLOW_IDS:
            raise WorkflowError(f"unsupported workflow id: {workflow_id!r}")
        prompt = payload.get("user_prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise WorkflowError("user_prompt must be a non-empty string")
        return cls(
            id=workflow_id,
            user_prompt=prompt,
            plugin_plan=PluginPlan.from_payload(payload.get("plugin_plan")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable workflow."""
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "user_prompt": self.user_prompt,
            "plugin_plan": self.plugin_plan.to_dict(),
        }


def _strings(value: object, name: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise WorkflowError(f"{name} must be an array")
    if not allow_empty and not value:
        raise WorkflowError(f"{name} must not be empty")
    if not all(isinstance(item, str) and item for item in value):
        raise WorkflowError(f"{name} must contain non-empty strings")
    return list(value)


def _is_resource_free_preview(command: str) -> bool:
    """Return whether a command is an allowed resource-free preview."""
    return (
        (command.startswith("sandbox ") and " preview " in f" {command} ")
        or command.startswith("sandbox cleanup")
        or command.startswith("python <plugin-root>/scripts/benchmark.py")
    )


def validate_workflow(payload: object) -> dict[str, Any]:
    """Validate one plugin workflow example."""
    return WorkflowExample.from_payload(payload).to_dict()


def plan_from_intent(intent: str, *, command: str | None = None) -> dict[str, Any]:
    """Build a resource-free starter plan for a named workflow intent."""
    if intent not in WORKFLOW_IDS:
        raise WorkflowError(f"unsupported workflow id: {intent!r}")
    command = command or "python -m pytest"
    examples = {
        "run-tests-safely": {
            "user_prompt": "Run this test suite in an isolated Modal Sandbox.",
            "preview_command": f"sandbox preview run {command}",
            "live_commands": [f"sandbox run {command}"],
        },
        "debug-failing-script": {
            "user_prompt": "Debug this failing script in a clean sandbox.",
            "preview_command": f"sandbox preview run {command}",
            "live_commands": [f"sandbox run {command}"],
        },
        "persistent-workspace": {
            "user_prompt": "Persist generated files across multiple sandbox runs.",
            "preview_command": f"sandbox --workspace-volume work preview run {command}",
            "live_commands": [f"sandbox --workspace-volume work run {command}"],
        },
        "reusable-coding-sandbox": {
            "user_prompt": "Start a reusable sandbox for iterative coding.",
            "preview_command": "sandbox --name agent-workspace preview start",
            "live_commands": ["sandbox --name agent-workspace start"],
        },
        "benchmark-two-approaches": {
            "user_prompt": "Benchmark two equivalent approaches under the same sandbox controls.",
            "preview_command": "python <plugin-root>/scripts/benchmark.py scenario.json --validate-only",
            "live_commands": ["python <plugin-root>/scripts/benchmark.py scenario.json --allow-live"],
        },
        "inspect-and-cleanup": {
            "user_prompt": "Inspect and clean up reusable sandbox resources.",
            "preview_command": "sandbox cleanup --app modal-sandbox-sdk",
            "live_commands": ["sandbox cleanup --app modal-sandbox-sdk --yes"],
        },
    }
    selected = examples[intent]
    return validate_workflow(
        {
            "schema_version": "1",
            "id": intent,
            "user_prompt": selected["user_prompt"],
            "plugin_plan": {
                "safe_commands": ["sandbox dry", "sandbox doctor", "sandbox schema --agent"],
                "preview_command": selected["preview_command"],
                "live_commands": selected["live_commands"],
                "cleanup_commands": ["sandbox status", "sandbox cleanup --app modal-sandbox-sdk"],
                "approval_required": True,
                "resource_boundary": "Live Modal commands require explicit user approval.",
            },
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", nargs="?", type=Path)
    parser.add_argument("--intent", choices=sorted(WORKFLOW_IDS))
    parser.add_argument("--command")
    parser.add_argument("--validate-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.workflow is not None:
            payload = json.loads(args.workflow.read_text(encoding="utf-8"))
            workflow = validate_workflow(payload)
        elif args.intent:
            workflow = plan_from_intent(args.intent, command=args.command)
        else:
            raise WorkflowError("provide a workflow file or --intent")
    except (OSError, json.JSONDecodeError, WorkflowError) as exc:
        print(json.dumps({"schema_version": "1", "status": "invalid_workflow", "error": {"message": str(exc)}}))
        return 2

    if args.validate_only:
        print(json.dumps({"schema_version": "1", "status": "valid", "resource_free": True, "id": workflow["id"]}))
    else:
        print(
            json.dumps(
                {"schema_version": "1", "status": "planned", "resource_free": True, "workflow": workflow}, indent=2
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
