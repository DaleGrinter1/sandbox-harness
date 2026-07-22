# Agent And MCP Notes

The public `modal-sandbox` plugin does not require MCP. It ships one end-user
skill at `plugins/modal-sandbox/skills/modal-sandbox/` and delegates execution
to the installed `sandbox` CLI. The skills under `.agents/skills/` remain
development helpers for agents working on the repository.

## Public Plugin

Install the package prerequisite and repo-local plugin:

```bash
pip install modal-sandbox-sdk
codex plugin marketplace add .agents/plugins
codex plugin add modal-sandbox@personal
```

Start a new Codex thread after installation or reinstall so `$modal-sandbox`
is loaded. The public skill checks for the CLI, runs safe discovery, verifies
authentication, chooses one-shot versus persistent workflows, and cleans up
agent-created long-lived sandboxes by default.

For a complete handoff prompt, use
[new-agent-prompt.md](new-agent-prompt.md). It tells agents how to start with
dry commands and how to use active execution-plan state.

Use the dry-command safe discovery sequence before creating Modal resources:

```bash
uv run sandbox dry
uv run sandbox schema --agent
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
```

`sandbox schema --agent` is the lowest-token machine-readable orientation
payload. It includes read order, repo-local skill routing, safe commands, live
Modal guardrails, golden workflows, and validation commands. A generated copy
lives at `docs/generated/agent-manifest.json`.

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

## Subagent Lanes

Use repo-local skills as lightweight subagent lanes. They are development
workflow guidance, not runtime package dependencies.

- `modal-sandbox-repo-understanding`: first-pass orientation, architecture,
  planning state, and safe discovery.
- `modal-sandbox-package-maintenance`: SDK, provider, CLI, packaging, tests,
  and release-facing changes.
- `modal-sandbox-cli-workflows`: CLI schema, dry commands, and live Modal
  workflow choices.
- `modal-sandbox-understanding-check`: coaching, quizzes, and architecture
  comprehension checks.

For broad work, one agent should own the active exec-plan feature while helper
agents read the same plan and report back with focused findings. Do not create
new agent config files unless a human explicitly asks for runnable agent
automation.
