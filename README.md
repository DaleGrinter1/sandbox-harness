# Modal Agent Sandbox Harness

Small Python harness for running commands and simple file workflows inside
Modal Sandboxes, with optional OpenAI Agents SDK tool wrappers.

```python
from modal_agent_sandbox import Sandbox

sandbox = Sandbox.create()
result = sandbox.run("python -c 'print(123)'")
print(result.stdout)
sandbox.close()
```

The default workspace is `/workspace` inside the Modal sandbox. File helpers
operate there by executing sandbox-side commands; they do not read or write the
local repository filesystem.

## CLI

```bash
sandbox-harness run "python -c 'print(123)'"
sandbox-harness write game.py --content "print('hello')"
sandbox-harness read game.py
sandbox-harness ls .
```

Commands print JSON for easy inspection.

## Agents SDK

The harness includes optional OpenAI Agents SDK helpers. You can use the default
sandbox agent or pass your own agent so callers can choose the agent behavior.

```python
from agents import Agent

from modal_agent_sandbox import Sandbox, run_sandbox_agent
from modal_agent_sandbox.agents_tools import make_sandbox_tools

async def main():
    with Sandbox.create() as sandbox:
        agent = Agent(
            name="My sandbox agent",
            instructions="Use the sandbox tools to edit and run files.",
            tools=make_sandbox_tools(sandbox),
        )
        result = await run_sandbox_agent(
            "Create game.py, then run it.",
            sandbox=sandbox,
            agent=agent,
        )
```

## Development

This repo uses `uv` for dependency management and local commands.

```bash
uv sync
uv run pytest
uv run sandbox-harness --help
uv run sandbox-harness run "python -c 'print(123)'"
```

## Modal Setup

Live runs require Modal credentials configured in your environment. Unit tests
use a fake provider and do not contact Modal.

Live Modal tests are opt-in:

```bash
SANDBOX_HARNESS_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_live.py
```
