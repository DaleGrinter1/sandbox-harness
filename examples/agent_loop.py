from __future__ import annotations

import asyncio

from agents import Agent

from modal_agent_sandbox import Sandbox, run_sandbox_agent
from modal_agent_sandbox.agents_tools import make_sandbox_tools


def make_agent(sandbox: Sandbox) -> Agent:
    return Agent(
        name="Sandbox assistant",
        instructions=(
            "Use the sandbox tools for shell commands and file operations. "
            "Files must be created inside the sandbox workspace."
        ),
        tools=make_sandbox_tools(sandbox),
    )


async def main() -> None:
    with Sandbox.create() as sandbox:
        result = await run_sandbox_agent(
            "Create game.py that prints hello, then run it.",
            sandbox=sandbox,
            agent=make_agent(sandbox),
        )
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
