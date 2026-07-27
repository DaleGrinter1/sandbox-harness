# Public Plugin Onboarding

## Promise

A new user with Codex, Python 3.11+, uv, and a Modal account can install the
public plugin from GitHub, verify local readiness without creating resources,
and reach an explicitly authorized first sandbox run in under five minutes.

## Installation Contract

```bash
uv tool install modal-sandbox-sdk
codex plugin marketplace add DaleGrinter1/sandbox-harness
codex plugin add modal-sandbox@personal
```

Start a new Codex thread after installation. Invoke `$modal-sandbox` in the
Codex composer, not in a shell.

The installation is repository-independent: Codex downloads the plugin from
the GitHub marketplace, while `uv tool` downloads the execution engine from
PyPI. Distributed plugin scripts resolve assets relative to their installed
plugin root and must work when the current directory is unrelated to this
repository.

The plugin requires CLI version 0.4.0 or newer and CLI schema version 1. It may
recommend `uv tool upgrade modal-sandbox-sdk`, but it must not install or
upgrade the CLI without explicit approval.

## First-Run Contract

1. Confirm `sandbox --version`.
2. Run `sandbox dry`, `sandbox doctor`, `sandbox schema --agent`, and
   `sandbox quickstart`; none may create Modal resources.
3. Stop with actionable setup guidance when authentication is unavailable.
4. Run `sandbox quickstart --run` only after an explicit live-execution request.
5. Report structured JSON results and clean up agent-created reusable sandboxes.

## Acceptance Scenarios

- Missing CLI produces the exact uv tool installation command.
- CLI versions below 0.4.0 produce the exact upgrade command and no live action.
- Readiness-only prompts remain resource-free.
- First live execution is announced before resource creation.
- One-shot, persistent-volume, and reusable-sandbox prompts select the correct workflow.
- Remote nonzero exit codes remain command results.
- Plugin installation works from the public GitHub marketplace in a fresh Codex configuration.
- A copied or downloaded plugin runs validate-only helpers from an unrelated
  working directory on Linux, macOS, and Windows.
