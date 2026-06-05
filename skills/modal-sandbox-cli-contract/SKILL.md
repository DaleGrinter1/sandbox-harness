---
name: modal-sandbox-cli-contract
description: CLI contract maintenance guidance for modal-sandbox-sdk. Use when Codex changes sandbox CLI commands, arguments, JSON output shapes, schema metadata, recipes, help text, tests, or docs so parser behavior, schema output, examples, and validation stay aligned.
---

# Modal Sandbox CLI Contract

Use this skill when changing `packages/sandbox_cli/cli.py` or any CLI-facing docs/tests.

## Contract Surfaces

Keep these in sync:

- Argument parser and command implementation in `packages/sandbox_cli/cli.py`.
- `COMMANDS_SCHEMA`, recipes, lifecycle notes, and image aliases in `cli.py`.
- CLI tests in `tests/test_cli.py`.
- README and `docs/cli.md` examples.
- Any skill instructions that mention affected commands.

## Change Workflow

1. Update parser arguments and runtime behavior together.
2. Update JSON schema payloads for command metadata, options, examples, and output fields.
3. Add or update fake-sandbox CLI tests before live tests.
4. Update docs and examples only after behavior is clear.
5. Run the narrow CLI validation:

```bash
uv run pytest tests/test_cli.py
uv run sandbox --help
```

## JSON Rules

- Commands should print JSON except `--help` and `--version`.
- Argument and runtime failures should use the JSON error envelope.
- Discovery commands must not create Modal resources.
- Preserve stable field names in existing JSON output unless intentionally making a breaking change.

## Safety Checks

- If adding a command that contacts Modal, mark it as live in schema lifecycle notes.
- If adding a discovery command, test that it does not instantiate `Sandbox`.
- If adding output fields, update tests to assert the shape.
- Keep command examples copy-pasteable with `uv run sandbox` in docs.
