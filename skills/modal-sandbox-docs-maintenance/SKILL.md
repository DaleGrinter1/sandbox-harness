---
name: modal-sandbox-docs-maintenance
description: Documentation maintenance guidance for modal-sandbox-sdk. Use when Codex changes README, docs, examples, skills, CLI schema text, setup guidance, development commands, or any user-facing workflow instructions and needs to prevent drift across repo documentation.
---

# Modal Sandbox Docs Maintenance

Use this skill when editing repo documentation, examples, or user-facing workflow text.

## Docs Map

- `README.md`: front door, quickstart, short SDK and CLI examples, links.
- `docs/cli.md`: detailed CLI workflows.
- `docs/modal-setup.md`: Modal authentication and SDK exception notes.
- `docs/agents.md`: agent-safe workflow and companion MCP notes.
- `docs/development.md`: validation commands and live test opt-in.
- `CONTRIBUTING.md`: contributor workflow and release checklist.
- `CHANGELOG.md`: user-visible change notes.
- `skills/*/SKILL.md`: portable agent instructions.

## Drift Checks

When changing commands, options, or workflow behavior, check:

- README quickstart.
- `docs/cli.md`.
- `uv run sandbox schema` descriptions in `packages/sandbox_cli/cli.py`.
- Examples under `examples/`.
- Relevant repo-local skills.
- Tests that pin docs or examples, especially `tests/test_packaging.py`.

## Style

- Keep README concise and link to detailed docs.
- Use `uv run sandbox ...` in repo docs.
- Label live Modal commands clearly when they create resources.
- Keep safe discovery commands grouped together:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox recipes
uv run sandbox quickstart
```

## Validation

Run at least:

```bash
uv run pytest tests/test_packaging.py
uv run sandbox --help
```

Run broader tests if docs changes also touch code, examples, or skills.
