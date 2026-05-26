# AGENTS.md

## Project Overview

- This project is `modal-sandbox-sdk`.
- It is a small Python harness for running commands and file workflows inside Modal Sandboxes.
- The public package is `sandbox`.
- Dependencies and commands are managed with `uv`; keep `uv.lock` in sync when dependencies change.

## Direction

- Keep the repo small, boring, and easy to extend.
- Keep the SDK focused on Modal Sandbox workflows.
- Sandbox file helpers must operate inside the Modal sandbox workspace, not on the local repository filesystem.
- Do not import broad framework features from older projects unless they directly support this SDK.

## Common Commands

- Sync dependencies: `uv sync`
- Run tests: `uv run pytest`
- Show CLI help: `uv run sandbox --help`
- Run a command in a sandbox: `uv run sandbox run "python -c 'print(123)'"`

## Testing

- Default tests must not create real Modal resources.
- Live Modal tests must stay opt-in behind `MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1`.
- When changing Python code, run the narrowest useful validation command available.
