from __future__ import annotations

import json

from .sandbox import Sandbox


def make_sandbox_tools(sandbox: Sandbox) -> list[object]:
    try:
        from agents import function_tool
    except ImportError as exc:
        raise RuntimeError("Install the 'openai-agents' package to create Agents SDK tools.") from exc

    @function_tool
    def run_command(command: str) -> str:
        """Run a shell command inside the Modal sandbox and return its result as JSON."""
        return json.dumps(sandbox.run(command).to_dict(), sort_keys=True)

    @function_tool
    def write_file(path: str, content: str) -> str:
        """Write a text file inside the Modal sandbox workspace."""
        return json.dumps(sandbox.write_file(path, content).to_dict(), sort_keys=True)

    @function_tool
    def read_file(path: str) -> str:
        """Read a text file from inside the Modal sandbox workspace."""
        return sandbox.read_file(path)

    @function_tool
    def list_files(path: str = ".") -> str:
        """List files from inside the Modal sandbox workspace."""
        return "\n".join(sandbox.list_files(path))

    return [run_command, write_file, read_file, list_files]
