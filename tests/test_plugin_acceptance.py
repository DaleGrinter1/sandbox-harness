from __future__ import annotations

import json
from pathlib import Path

import pytest

PLUGIN_ROOT = Path("plugins/modal-sandbox")
SKILL_ROOT = PLUGIN_ROOT / "skills" / "modal-sandbox"
SKILL = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
WORKFLOWS = {
    payload["id"]: payload
    for path in (PLUGIN_ROOT / "examples").glob("*.json")
    if "plugin_plan" in (payload := json.loads(path.read_text(encoding="utf-8")))
}


@pytest.mark.parametrize(
    ("scenario", "required_guidance"),
    [
        ("missing CLI", "uv tool install modal-sandbox-sdk"),
        ("outdated CLI", "uv tool upgrade modal-sandbox-sdk"),
        ("safe discovery", "sandbox schema --agent"),
        ("workflow compatibility", "--check-compatibility"),
        ("approval boundary", "Ask for explicit approval before `live_commands`"),
        ("verification", "run `verification_commands`"),
        ("cleanup approval", "cleanup command containing `--yes`"),
        ("remote failure", "nonzero remote exit is a completed command result"),
    ],
)
def test_public_skill_covers_core_acceptance_scenario(scenario: str, required_guidance: str) -> None:
    assert required_guidance in SKILL, scenario


def test_public_skill_orders_safe_preflight_before_live_boundary() -> None:
    assert SKILL.index("## Safe Workflow") < SKILL.index("## Live-Action Boundary")
    assert SKILL.index("Run every `preview_commands`") < SKILL.index("Ask for explicit approval")
    assert (
        "planning, explanation,\n   preview, benchmark-design, or readiness-only request never grants approval" in SKILL
    )


def test_public_skill_routes_every_distributed_workflow() -> None:
    expected = {
        "run-tests-safely",
        "debug-failing-script",
        "persistent-workspace",
        "reusable-coding-sandbox",
        "seed-and-test-project",
        "service-with-readiness",
        "resource-controlled-job",
        "filesystem-inspection",
        "benchmark-two-approaches",
        "inspect-and-cleanup",
    }

    assert set(WORKFLOWS) == expected
    for workflow_id, workflow in WORKFLOWS.items():
        assert f"`{workflow_id}`" in SKILL
        plan = workflow["plugin_plan"]
        assert plan["required_cli_schema"] == "1"
        assert plan["approval_required"] is True
        assert plan["preview_commands"]
        assert plan["expected_result_fields"]
        assert plan["recovery_guidance"]


def test_public_skill_uses_progressive_disclosure_for_recipes_and_recovery() -> None:
    recipes = (SKILL_ROOT / "references" / "workflow-recipes.md").read_text(encoding="utf-8")
    recovery = (SKILL_ROOT / "references" / "results-and-recovery.md").read_text(encoding="utf-8")

    assert "references/workflow-recipes.md" in SKILL
    assert "references/results-and-recovery.md" in SKILL
    assert "## Public Source" in recipes
    assert "## Services and Readiness" in recipes
    assert "## Resource and Network Controls" in recipes
    assert "cli_not_found" in recovery
    assert "## Readiness Failures" in recovery
    assert "## Cleanup Failures" in recovery
