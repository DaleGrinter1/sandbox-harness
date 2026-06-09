# Agent And MCP Notes

This package does not require MCP at runtime. MCPs and repo-local skills are development helpers for agents working on the repository.

Use the safe discovery sequence before creating Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
```

If `doctor` reports `ready: true`, the first live verification command is:

```bash
uv run sandbox --image py313 quickstart --run
```

After that, use `sandbox run` for one-off commands or `sandbox start` plus `--sandbox-id` for a longer workflow.

Optional repo-local Codex-style skills live in `.codex/skills`. They are source artifacts for agents and are not required at package runtime. For a new user, start with `.codex/skills/modal-sandbox-first-run/SKILL.md`; use the other focused skills for CLI workflows, file workflows, Python SDK workflows, CLI contract changes, provider changes, docs maintenance, and live Modal tests.

To use a skill with an agent, point the agent at the relevant `SKILL.md` and ask it to follow that workflow.

## Recommended Companion MCPs

- **Context7**: use for up-to-date, version-specific library documentation.
- **OpenAI developer docs MCP**: use for current OpenAI API and Codex documentation.
- **Chrome DevTools MCP**: use when browser inspection is relevant to future frontend work.

Useful references:

- Context7 docs: <https://context7.com/docs>
- OpenAI developer docs: <https://developers.openai.com/>
- Chrome DevTools MCP: <https://github.com/ChromeDevTools/chrome-devtools-mcp>
