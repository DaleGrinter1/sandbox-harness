---
name: modal-sandbox-first-run
description: Beginner first-run workflow for modal-sandbox-sdk. Use when Codex needs to help a user or agent safely get started with the sandbox CLI, inspect available commands, check Modal readiness, preview workflows, and run the first short-lived Modal Sandbox verification.
---

# Modal Sandbox First Run

Use this skill when the user is new to `modal-sandbox-sdk` or asks for the safest first path.

## Workflow

1. Start with safe discovery commands that do not create Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox recipes
uv run sandbox quickstart
```

2. Inspect JSON fields before recommending live commands:
   - Treat `creates_modal_resources` as the safety signal.
   - Treat `doctor.ready` as the readiness signal.
   - If credentials are missing, recommend `uv run modal setup`.

3. Use the first live verification only after readiness is clear:

```bash
uv run sandbox --image py313 quickstart --run
```

4. After the live check succeeds, choose the next path from `sandbox recipes`:
   - One-shot command: `sandbox --image py313 run "..."`
   - Persistent files: add `--workspace-volume my-workspace`.
   - Longer live workflow: use `sandbox start`, reuse `--sandbox-id`, then `sandbox stop`.

## Guardrails

- Do not run live Modal commands until the user has opted into creating resources.
- Prefer CLI image aliases such as `py313`; the CLI resolves them to registry tags.
- If a command errors, run `uv run sandbox doctor` before guessing at Modal setup.
- Live Modal tests and real Modal resources are opt-in.
