# Agent And MCP Notes

This package does not require MCP at runtime. MCPs are useful companion tools
for agents working on the repo or building projects around it.

Use the safe discovery sequence before creating Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox recipes
uv run sandbox quickstart
```

If `doctor` reports `ready: true`, the first live verification command is:

```bash
uv run sandbox --image py313 quickstart --run
```

After that, use `sandbox run` for one-off commands or `sandbox start` plus
`--sandbox-id` for a longer workflow.

Optional repo-local Codex-style skills live in `skills/`. They are source
artifacts for agents and are not required at package runtime. For a new user,
start with `skills/modal-sandbox-first-run/SKILL.md`; use the other focused
skills for CLI workflows, file workflows, Python SDK workflows, CLI contract
changes, provider changes, docs maintenance, and live Modal tests.

To use a skill with an agent, point the agent at the relevant `SKILL.md` and
ask it to follow that workflow. Suggested starting prompts:

```text
Use skills/modal-sandbox-first-run/SKILL.md to help me verify my Modal setup.
Use skills/modal-sandbox-cli-workflows/SKILL.md to run this command safely.
Use skills/modal-sandbox-file-workflows/SKILL.md to persist files across CLI calls.
Use skills/modal-sandbox-python-sdk/SKILL.md to write Python code with this SDK.
Use skills/modal-sandbox-cli-contract/SKILL.md to change a CLI command safely.
Use skills/modal-sandbox-provider-adapter/SKILL.md to update provider behavior.
Use skills/modal-sandbox-docs-maintenance/SKILL.md to keep docs and examples aligned.
Use skills/modal-sandbox-live-tests/SKILL.md to run opt-in Modal integration tests.
```

These skills are portable Markdown instructions. They do not install
automatically, do not affect package imports, and can be copied into an
agent-specific skills directory if that agent supports one.

## Recommended Companion MCPs

- **Context7**: use for up-to-date, version-specific library documentation.
  Helpful when agents need current Modal, Python packaging, or `pytest` docs.
- **Google MCP collection**: use as the starting point for Google's MCP servers,
  including Google Cloud, Google Workspace, Chrome DevTools, and related tools.
- **gcloud MCP**: use when agents need to inspect or operate Google Cloud
  projects through the `gcloud` CLI.
- **MCP Toolbox for Databases**: use only if this project grows examples around
  BigQuery, Cloud SQL, AlloyDB, Spanner, Firestore, or PostgreSQL.
- **Notion MCP**: use when project docs, task notes, specs, or release notes
  live in Notion. The hosted MCP endpoint is `https://mcp.notion.com/mcp`.
- **Slack MCP**: use when agents need project discussion history, decisions,
  status updates, channels, threads, or canvases from Slack. The hosted MCP
  endpoint is `https://mcp.slack.com/mcp`.

The same list is exposed in:

```bash
uv run sandbox schema
```

Useful references:

- Context7 docs: <https://context7.com/docs>
- Google MCP collection: <https://github.com/google/mcp>
- gcloud MCP: <https://github.com/googleapis/gcloud-mcp>
- MCP Toolbox for Databases: <https://github.com/googleapis/mcp-toolbox>
- Notion MCP docs: <https://developers.notion.com/guides/mcp/overview>
- Slack MCP docs: <https://docs.slack.dev/ai/slack-mcp-server/>
