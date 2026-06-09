# Codex Workspace Helpers

This folder keeps repo-local Codex configuration used while working on
`modal-sandbox-sdk`. These files are development helpers, not part of the
public Python package or CLI contract.

## MCP Servers

`.codex/config.toml` mirrors the useful MCP server entries from
`/Users/dalegrinter/.codex/config.toml`:

- `openaiDeveloperDocs`
- `context7`
- `chrome-devtools`

Keep personal project trust entries in the home Codex config. Keep reusable MCP
server definitions here when they are useful for this repository.

## Skills

Optional Codex-style skills live in `.codex/skills/`. They are source
instructions for agent workflows, not package runtime files.

- `modal-sandbox-first-run`: verify Modal setup and first execution.
- `modal-sandbox-cli-workflows`: operate the JSON CLI safely.
- `modal-sandbox-file-workflows`: work with sandbox files and volumes.
- `modal-sandbox-python-sdk`: write Python SDK examples.
- `modal-sandbox-cli-contract`: change CLI behavior and tests together.
- `modal-sandbox-provider-adapter`: update Modal provider behavior.
- `modal-sandbox-docs-maintenance`: keep docs and examples aligned.
- `modal-sandbox-live-tests`: run opt-in Modal integration tests.

Example prompts:

```text
Use .codex/skills/modal-sandbox-first-run/SKILL.md to help me verify my Modal setup.
Use .codex/skills/modal-sandbox-cli-workflows/SKILL.md to run this command safely.
Use .codex/skills/modal-sandbox-file-workflows/SKILL.md to persist files across CLI calls.
```

These skills are portable Markdown instructions. They do not install
dependencies, start servers, or create Modal resources by themselves.
