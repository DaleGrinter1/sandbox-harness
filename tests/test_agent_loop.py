from __future__ import annotations

import asyncio

import pytest
from modal_agent_sandbox import CommandResult, Sandbox, SandboxConfig
from modal_agent_sandbox import agent_loop


class FakeProvider:
    def __init__(self) -> None:
        self.config = SandboxConfig(use_volume=False)
        self.closed = False

    def run(self, command: str, timeout: int | None = None, cwd: str | None = None) -> CommandResult:
        return CommandResult(command, "", "", 0, 1)

    def close(self) -> None:
        self.closed = True


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[object, str]] = []

    async def run(self, agent: object, prompt: str) -> str:
        self.calls.append((agent, prompt))
        return "done"


def test_run_sandbox_agent_accepts_a_custom_agent() -> None:
    provider = FakeProvider()
    sandbox = Sandbox.from_provider(provider)
    runner = FakeRunner()
    custom_agent = object()

    result = asyncio.run(
        agent_loop.run_sandbox_agent(
            "write a file",
            sandbox=sandbox,
            agent=custom_agent,
            runner=runner,
        )
    )

    assert result == "done"
    assert runner.calls == [(custom_agent, "write a file")]
    assert provider.closed is False


def test_run_sandbox_agent_accepts_an_agent_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeProvider()
    sandbox = Sandbox.from_provider(provider)
    runner = FakeRunner()
    tools = [object()]

    monkeypatch.setattr(agent_loop, "make_sandbox_tools", lambda sandbox: tools)

    def agent_factory(received_sandbox: Sandbox, received_tools: list[object]) -> dict[str, object]:
        return {"sandbox": received_sandbox, "tools": received_tools}

    result = asyncio.run(
        agent_loop.run_sandbox_agent(
            "run tests",
            sandbox=sandbox,
            agent_factory=agent_factory,
            runner=runner,
        )
    )

    assert result == "done"
    assert runner.calls == [({"sandbox": sandbox, "tools": tools}, "run tests")]


def test_run_sandbox_agent_rejects_agent_and_factory() -> None:
    with pytest.raises(ValueError, match="either agent or agent_factory"):
        asyncio.run(
            agent_loop.run_sandbox_agent(
                "ambiguous",
                sandbox=Sandbox.from_provider(FakeProvider()),
                agent=object(),
                agent_factory=lambda sandbox, tools: object(),
                runner=FakeRunner(),
            )
        )
