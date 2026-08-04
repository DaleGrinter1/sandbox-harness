# Exec Plans Index

Execution plans are durable artifacts for long-running or cross-cutting work.

## Active

- None.

## Completed

- [Plugin Maturity](completed/plugin-maturity/PLAN_plugin-maturity.md)
- [Assessment Remediation](completed/assessment-remediation/PLAN_assessment-remediation.md)
- [Plugin-First Product](completed/plugin-first-product/PLAN_plugin-first-product.md)
- [Modal Native Sandbox Expansion](completed/modal-native-sandbox-expansion/PLAN_modal-native-sandbox-expansion.md)
- [Repository Knowledge System](completed/repository-knowledge-system/PLAN_repository-knowledge-system.md)
- [Release Readiness Hardening](completed/release-readiness-hardening/PLAN_release-readiness-hardening.md)
- [Sandbox Workflow Expansion](completed/sandbox-workflow-expansion/PLAN_sandbox-workflow-expansion.md)
- [Public Plugin Onboarding](completed/public-plugin-onboarding/PLAN_public-plugin-onboarding.md)
- [Plugin First Product Experience](completed/plugin-first-product-experience/PLAN_plugin-first-product-experience.md)
- [CLI Plugin Experience](completed/cli-plugin-experience/PLAN_cli-plugin-experience.md)
- [Senior Review Remediation and Usability](completed/senior-review-remediation-and-usability/PLAN_senior-review-remediation-and-usability.md)

## Workflow Summary

- Use markdown for narrative plans.
- Use `state/feature-list.json` for implementation checklist state.
- Use `state/session-state.json` for active feature, blockers, next action, and handoff.
- Use `state/progress.jsonl` for append-only checkpoints.
- Do not use markdown task files by default.

Validate with:

```bash
./scripts/execplan/check.sh
```
