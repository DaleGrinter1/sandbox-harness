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

Optional repo-local skills live in `.agents/skills`, the project path used by
the Vercel Labs `skills` CLI for Codex. They are source artifacts for agents
and are not required at package runtime.

Use:

- `.agents/skills/modal-sandbox-repo-understanding/SKILL.md` for repo
  orientation and planning context.
- `.agents/skills/modal-sandbox-cli-workflows/SKILL.md` for safe CLI and live
  Modal workflow choices.
- `.agents/skills/modal-sandbox-understanding-check/SKILL.md` for quizzing or
  coaching users on repo architecture, workflows, docs, and validation rules.
- `.agents/skills/modal-sandbox-package-maintenance/SKILL.md` for SDK, CLI,
  provider, docs, tests, and packaging changes.

Useful `skills` CLI commands:

```bash
npx skills list --agent codex
npx skills add vercel-labs/agent-skills --list
npx skills find modal
```

To use a project skill manually, point the agent at the relevant `SKILL.md` and
ask it to follow that workflow.

## Modal's Upstream Skill

Modal SDK 1.5.0 also ships a separate `modal skills` CLI for installing
Modal's own foundational agent skill. It is a useful companion for general
Modal API guidance, while the `modal-sandbox-*` skills above remain the source
of truth for this package's boundaries and tests.

Use safe discovery first:

```bash
uv run modal skills show
```

Then install or update it if you want that Modal-owned context in the project:

```bash
uv run modal skills install --yes
uv run modal skills update --yes
```

Review generated files before committing them. Modal's installed skill is
named `modal` and is expected to install under `.agents/skills/modal` for
project installs. It is developer context, not runtime package code.

## Recommended Companion MCPs

- **Context7**: use for up-to-date, version-specific library documentation.
- **OpenAI developer docs MCP**: use for current OpenAI API and Codex documentation.
- **Chrome DevTools MCP**: use when browser inspection is relevant to future frontend work.

Useful references:

- Context7 docs: <https://context7.com/docs>
- OpenAI developer docs: <https://developers.openai.com/>
- Chrome DevTools MCP: <https://github.com/ChromeDevTools/chrome-devtools-mcp>
