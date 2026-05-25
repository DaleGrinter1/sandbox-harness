from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .agents_tools import make_sandbox_tools
from .sandbox import Sandbox


AgentFactory = Callable[[Sandbox, list[object]], object]

DEFAULT_AGENT_NAME = "Sandbox assistant"
DEFAULT_AGENT_INSTRUCTIONS = (
    "Use the sandbox tools for shell commands and file operations. "
    "Files must be created inside the sandbox workspace."
)


def create_default_agent(sandbox: Sandbox, tools: list[object] | None = None) -> object:
    try:
        from agents import Agent
    except ImportError as exc:
        raise RuntimeError("Install the 'openai-agents' package to create Agents SDK agents.") from exc

    if tools is None:
        tools = make_sandbox_tools(sandbox)

    return Agent(
        name=DEFAULT_AGENT_NAME,
        instructions=DEFAULT_AGENT_INSTRUCTIONS,
        tools=tools,
    )


async def run_sandbox_agent(
    prompt: str,
    *,
    sandbox: Sandbox | None = None,
    agent: object | None = None,
    agent_factory: AgentFactory | None = None,
    runner: Any | None = None,
) -> object:
    if agent is not None and agent_factory is not None:
        raise ValueError("Pass either agent or agent_factory, not both.")

    owns_sandbox = sandbox is None
    sandbox = sandbox or Sandbox.create()

    try:
        if runner is None:
            try:
                from agents import Runner
            except ImportError as exc:
                raise RuntimeError("Install the 'openai-agents' package to run Agents SDK agents.") from exc

            runner = Runner

        if agent is None:
            tools = make_sandbox_tools(sandbox)
            factory = agent_factory or create_default_agent
            agent = factory(sandbox, tools)

        return await runner.run(agent, prompt)
    finally:
        if owns_sandbox:
            sandbox.close()
