# New Agent Starter Prompt

Use this prompt when assigning a new agent meaningful work in this repository.
It is intentionally specific to `modal-sandbox-sdk` so the agent starts with
safe discovery, current planning state, and the repo's product boundaries.

```text
You are working in the modal-sandbox-sdk repository.

First orient from the repo, not memory:
- Read AGENTS.md.
- Read ARCHITECTURE.md.
- Read docs/PRODUCT_SENSE.md.
- Read docs/references/cli.md.
- Read docs/exec-plans/index.md.

Product boundary:
- This is a lightweight Python SDK and JSON-first CLI for Modal Sandboxes.
- It is not a generic sandbox platform.
- Keep Modal imported lazily.
- Default tests and discovery must not create real Modal resources.

Start with dry commands only:
- uv run sandbox schema
- uv run sandbox doctor
- uv run sandbox quickstart
- ./scripts/dev/quickstart.sh

Do not run live Modal commands unless the user explicitly asks for live
execution. Live commands include quickstart --run, run, run-command, start,
stop, write, read, ls, mkdir, rm, upload, download, domain, and snapshot.
Live tests must stay opt-in with MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1.

Before broad work, make sure the exec plan is being used:
- Read docs/PLANS.md.
- Read docs/exec-plans/index.md.
- If an active initiative exists, read its PLAN_<initiative>.md.
- Then read state/session-state.json, state/feature-list.json, and
  state/progress.jsonl.
- Work on one active feature at a time.
- Append progress entries instead of editing old JSONL lines.
- Mark a feature passes: true only after validation evidence exists.
- Validate state with ./scripts/execplan/check.sh.

For implementation:
- Keep SDK, provider, CLI schema, docs, and tests moving together.
- Run the narrowest useful tests first.
- Before handoff, update session-state.json with the next action.
- Do not add Modal token values, token placeholders, or secrets.
```

## Dry Commands

Dry commands are the safe discovery commands that do not create Modal
resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
./scripts/dev/quickstart.sh
```

The machine-readable CLI schema exposes the same concept under
`lifecycle.dry_commands` and `lifecycle.safe_discovery_commands`.

## Exec-Plan Check

When a task touches public API, CLI behavior, provider behavior, docs
governance, or release work, check the active execution plan before editing.
The plan narrative explains why the work exists; the JSON state files tell the
agent what to do next.
