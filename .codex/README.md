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

Project skills live in `.agents/skills/`, matching the Vercel Labs `skills`
CLI project path for Codex. `.codex/` is reserved for Codex configuration and
MCP notes.

Current repo skills:

- `modal-sandbox-repo-understanding`: read order, product shape, architecture,
  golden workflows, and exec-plan state.
- `modal-sandbox-cli-workflows`: safe discovery, live CLI workflow choices,
  persistence, reuse, and live-test guardrails.
- `modal-sandbox-package-maintenance`: SDK/provider/CLI/docs change map and
  validation matrix.

Useful `skills` CLI commands:

```bash
npx skills list --agent codex
npx skills add vercel-labs/agent-skills --list
npx skills find modal
```

The repo skills are portable Markdown instructions. They do not install
dependencies, start servers, or create Modal resources by themselves.
