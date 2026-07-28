from __future__ import annotations

from pathlib import Path

import pytest

SKILL = Path("plugins/modal-sandbox/skills/modal-sandbox/SKILL.md").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("scenario", "required_guidance"),
    [
        ("missing CLI", "uv tool install modal-sandbox-sdk"),
        ("outdated CLI", "uv tool upgrade modal-sandbox-sdk"),
        ("safe discovery", "sandbox schema --agent"),
        ("first-run preview", "sandbox quickstart"),
        ("one-shot execution", "sandbox run` or `sandbox run-command"),
        ("persistent files", "--workspace-volume NAME"),
        ("reusable sandbox", "--name NAME start"),
        ("preview before live", "sandbox preview ..."),
        ("cleanup approval", "cleanup --yes"),
        ("workflow planner", "scripts/workflow.py"),
        ("remote failure", "nonzero sandbox command exit"),
    ],
)
def test_public_skill_covers_acceptance_scenario(scenario: str, required_guidance: str) -> None:
    assert required_guidance in SKILL, scenario


def test_public_skill_orders_safe_preflight_before_live_boundary() -> None:
    assert SKILL.index("## Preflight") < SKILL.index("## Live-Action Boundary")
    assert "Run `sandbox quickstart --run` only when the user explicitly asks" in SKILL
    assert "Never change the user's Python\n   environment without explicit approval" in SKILL


def test_public_skill_exposes_plugin_first_workflow_examples() -> None:
    examples = [
        "run-tests-safely.json",
        "debug-failing-script.json",
        "persistent-workspace.json",
        "reusable-coding-sandbox.json",
        "benchmark-two-approaches.json",
        "inspect-and-cleanup.json",
    ]

    for example in examples:
        assert example in SKILL
    assert "The `sandbox` CLI is the JSON engine" in SKILL
