---
name: modal-sandbox-repo-understanding
description: Repo orientation for modal-sandbox-sdk. Use when an agent needs to understand the repository purpose, architecture, product direction, docs map, golden workflows, or execution-plan state before making changes.
---

# Modal Sandbox Repo Understanding

Use this skill at the start of broad or ambiguous work. Treat the repository as
the source of truth and prefer canonical docs over stale conversation memory.

## Read Order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/PRODUCT_SENSE.md`
4. `docs/references/cli.md`
5. Relevant files in `packages/sandbox/` or `packages/sandbox_cli/`

For long-running work, also read `docs/PLANS.md` and
`docs/exec-plans/index.md`.

## Product Shape

This repo is a small Python SDK and JSON-first CLI for Modal Sandbox command,
file, port, and volume workflows. It is not a general sandbox platform.

The core promise is:

- safe discovery before creating Modal resources
- predictable command and file behavior inside Modal sandboxes
- explicit persistence through Modal volumes
- agent-readable CLI metadata through `sandbox schema`

## Golden Workflow Source

Inspect the machine-readable workflow contract with:

```bash
uv run sandbox schema
```

The schema includes `golden_workflows` for safe discovery, short-lived command
execution, persistent workspace files, and long-lived sandbox reuse.

## Planning State

Active plans live under `docs/exec-plans/active/` and use:

- one `PLAN_<initiative>.md`
- `state/feature-list.json`
- `state/session-state.json`
- `state/progress.jsonl`

Validate plan state with:

```bash
./scripts/execplan/check.sh
```
