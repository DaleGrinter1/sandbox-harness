# Modal Skills

Modal SDK 1.5.0 includes a `modal skills` CLI for installing and updating
Modal's upstream agent skill. This is useful companion context for agents that
work with Modal itself.

This repo also has repo-local skills under `.agents/skills/`. Keep the two
layers separate:

- Use Modal's upstream skill for general Modal API and platform guidance.
- Use this repo's `modal-sandbox-*` skills for package boundaries, CLI
  workflows, tests, docs, and maintenance rules.

## Commands

Inspect the upstream skill before installing it:

```bash
uv run modal skills show
```

Install it into this project:

```bash
uv run modal skills install --yes
```

Update an installed copy:

```bash
uv run modal skills update --yes
```

Useful options from Modal's CLI:

- `--no-docs` skips downloading Modal documentation resources.
- `--global` installs in the user home directory instead of the current repo.
- `--claude` installs to `.claude/` instead of `.agents/`.

## Repository Notes

Do not treat Modal's installed upstream skill as part of the packaged SDK. It is
developer context, not runtime code.

Before committing files created by `modal skills install`, review the generated
paths and decide whether they belong in the repo. The upstream skill is named
`modal` and is expected to install under `.agents/skills/modal` for project
installs. The repo-owned skills are the four `modal-sandbox-*` directories
already tracked under `.agents/skills/`, and `skills-lock.json` records that
current local skill state.

Safe Modal-skill commands do not create sandbox resources. Live sandbox
resource creation still starts with `sandbox quickstart --run`, `sandbox run`,
or `sandbox start`.
