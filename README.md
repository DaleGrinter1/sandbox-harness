# Modal Sandbox SDK

Small Python SDK and CLI for running commands and file workflows inside Modal
Sandboxes.

Use it when you want to:

- Run a command in a fresh Modal Sandbox.
- Write, read, list, remove, upload, or download sandbox files.
- Keep files across CLI calls with an optional Modal volume.
- Give agents a JSON-friendly CLI they can inspect before they act.

## Quick Start

Install dependencies for this repo:

```bash
uv sync
```

Inspect the CLI contract without creating Modal resources:

```bash
uv run sandbox schema
```

Check whether Modal is installed and credentials appear to be configured:

```bash
uv run sandbox doctor
```

Preview the first live sandbox command:

```bash
uv run sandbox quickstart
```

If `doctor` reports missing credentials, sign in to Modal:

```bash
uv run modal setup
```

If your shell cannot find the `modal` command, use:

```bash
uv run python -m modal setup
```

Run the beginner quickstart in a short-lived Modal Sandbox:

```bash
uv run sandbox --image python:3.13-slim quickstart --run
```

Then run any command:

```bash
uv run sandbox --image python:3.13-slim run "python -c 'print(123)'"
```

## Python SDK

The public package is `sandbox`.

```python
from sandbox import Images, Sandbox

with Sandbox.create(image=Images.PY313) as sb:
    sb.write_text("hello.py", "print('hello from Modal')\n")
    result = sb.run("python hello.py")
    print(result.stdout)
```

The default workspace is `/workspace` inside the Modal sandbox. Relative paths
are resolved there:

```python
with Sandbox.create(image=Images.PY313) as sb:
    sb.write_text("notes/todo.txt", "ship it\n")
    print(sb.read_text("notes/todo.txt"))
```

Use a raw registry image string when you need a different base image:

```python
with Sandbox.create(image="python:3.12-slim") as sb:
    print(sb.run("python --version").stdout)
```

Pass environment variables:

```python
with Sandbox.create(image=Images.PY313, env={"APP_ENV": "dev"}) as sb:
    print(sb.run("echo $APP_ENV").stdout)
```

Copy files between your machine and the sandbox:

```python
with Sandbox.create(image=Images.PY313) as sb:
    sb.copy_from_local("input.txt", "input.txt")
    sb.run("cp input.txt output.txt")
    sb.copy_to_local("output.txt", "output.txt")
```

Use a workspace volume when files should persist after the sandbox command:

```python
with Sandbox.create(workspace_volume="my-workspace") as sb:
    sb.write_text("notes.txt", "persistent content\n")
```

## SDK Methods

The `Sandbox` object exposes a small synchronous API:

```python
sb.run("python hello.py")
sb.write_text("hello.py", "print('hello')\n")
sb.read_text("hello.py")
sb.write_bytes("data.bin", b"hello")
sb.read_bytes("data.bin")
sb.list_files(".")
sb.mkdir("notes")
sb.remove("notes", recursive=True)
sb.copy_from_local("local.txt", "remote.txt")
sb.copy_to_local("remote.txt", "local.txt")
sb.close()
```

## CLI

The CLI command is `sandbox`. Commands print JSON except for `--help` and
`--version`.

Agent-friendly discovery commands do not create Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
```

`sandbox schema` prints command metadata, output shapes, lifecycle notes, path
rules, optional companion MCPs, auth setup commands, and examples as JSON.
`sandbox doctor` reports whether the Modal Python package is importable and
whether credentials appear to be configured through environment variables or
`~/.modal.toml`, plus beginner next steps.
`sandbox quickstart` previews a first live command without creating resources.
Use `sandbox quickstart --run` to create a short-lived sandbox and run
`python -c 'print(123)'`.

## For AI Agents

Use the safe discovery sequence before creating Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
```

If `doctor` reports `ready: true`, the first live verification command is:

```bash
uv run sandbox --image python:3.13-slim quickstart --run
```

After that, use `sandbox run` for one-off commands or `sandbox start` plus
`--sandbox-id` for a longer workflow.

Run a command:

```bash
uv run sandbox --image python:3.13-slim run "python -c 'print(123)'"
```

Create a reusable sandbox for a longer agent workflow:

```bash
uv run sandbox --image python:3.13-slim start
```

The output includes a `sandbox_id`. Reuse it with `--sandbox-id`:

```bash
uv run sandbox --sandbox-id sb-abc123 write hello.py --content "print('hello')"
uv run sandbox --sandbox-id sb-abc123 run "python hello.py"
uv run sandbox --sandbox-id sb-abc123 read hello.py
```

Terminate it when you are done:

```bash
uv run sandbox stop sb-abc123
```

By default, `sandbox run` exits with status `0` when the SDK call succeeds,
even if the command inside the sandbox exits nonzero. Use
`--use-command-exit-code` when shell scripts should receive the sandbox
command's exit status:

```bash
uv run sandbox run --use-command-exit-code "python -c 'raise SystemExit(7)'"
```

Run a small file workflow with a persistent workspace volume:

```bash
uv run sandbox --image python:3.13-slim --workspace-volume my-workspace write game.py --content "print('hello')"
uv run sandbox --image python:3.13-slim --workspace-volume my-workspace ls .
uv run sandbox --image python:3.13-slim --workspace-volume my-workspace run --cwd /workspace "python game.py"
uv run sandbox --image python:3.13-slim --workspace-volume my-workspace read game.py
```

Copy files in and out:

```bash
uv run sandbox --image python:3.13-slim --workspace-volume my-workspace upload input.txt input.txt
uv run sandbox --image python:3.13-slim --workspace-volume my-workspace download output.txt output.txt
```

Create and remove directories:

```bash
uv run sandbox --workspace-volume my-workspace mkdir notes
uv run sandbox --workspace-volume my-workspace rm notes --recursive
```

## Paths And Lifecycle

Relative paths are resolved inside the sandbox workspace, which defaults to
`/workspace`. Absolute paths are used as-is inside the sandbox.

Relative paths cannot use `..` to escape the workspace. This keeps helpers like
`write_text("notes/todo.txt", "...")` focused on the sandbox workspace.

Each CLI command creates or attaches to a sandbox, performs one operation, and
then closes it. Created one-shot sandboxes are terminated on close. Sandboxes
attached with `--sandbox-id` are detached on close and keep running.

Use `start` when separate CLI calls should share one live sandbox. Use
`--workspace-volume` when separate sandbox lifetimes need to share files.

Stop long-lived sandboxes explicitly:

```bash
uv run sandbox stop sb-abc123
```

## Agent And MCP Notes

This package does not require MCP at runtime. MCPs are useful companion tools
for agents working on the repo or building projects around it.

Recommended companion MCPs:

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

## Modal Setup

Live runs require Modal credentials. If you are new to Modal, create/sign in to
your Modal account and run:

```bash
uv run modal setup
```

For non-interactive environments such as CI, configure a Modal token instead:

```bash
uv run modal token new
uv run modal token set --token-id <token id> --token-secret <token secret>
```

You can also set `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` in the process
environment. Modal documents the setup flow in its
[getting started guide](https://modal.com/docs/guide) and token options in the
[`modal token` CLI reference](https://modal.com/docs/reference/cli/token).

When Modal reports missing, invalid, or expired credentials, this SDK raises
`ModalAuthenticationError` with setup commands so CLI users and Python callers
get a next step instead of a raw Modal traceback.

## Development

Default tests do not create real Modal resources.

```bash
uv sync
uv run pytest
uv run sandbox --help
```

Live Modal tests are opt-in:

```bash
MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_live.py
```
