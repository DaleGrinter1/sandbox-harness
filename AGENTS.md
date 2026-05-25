# AGENTS.md

## Project Overview

- This project is `modal-agent-sandbox`.
- It is a small Python harness for running commands and file workflows inside Modal Sandboxes.
- The public package is `modal_agent_sandbox`.
- Dependencies and commands are managed with `uv`; keep `uv.lock` in sync when dependencies change.

## Direction

- Keep the repo small, boring, and easy to extend.
- Keep Modal-specific code isolated from OpenAI Agents SDK tool code.
- Sandbox file helpers must operate inside the Modal sandbox workspace, not on the local repository filesystem.
- Do not import broad framework features from older projects unless they directly support this harness.

## Common Commands

- Sync dependencies: `uv sync`
- Run tests: `uv run pytest`
- Show CLI help: `uv run sandbox-harness --help`
- Run a command in a sandbox: `uv run sandbox-harness run "python -c 'print(123)'"`

## Testing

- Default tests must not create real Modal resources.
- Live Modal tests must stay opt-in behind `SANDBOX_HARNESS_RUN_MODAL_TESTS=1`.
- When changing Python code, run the narrowest useful validation command available.
