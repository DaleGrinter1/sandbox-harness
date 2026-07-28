# Product Sense

`modal-sandbox` helps agents run tasks that need isolated, reproducible, or
resource-controlled execution in short-lived or reusable Modal Sandboxes. The
plugin is the main product surface and uses the public `modal-sandbox-sdk` JSON
CLI as its execution engine. The SDK remains available to developers directly,
but it should stay quiet and focused unless SDK changes improve plugin
workflows. Neither layer replaces Modal's backend or full SDK.

## Target Users

- Agents that need isolated execution, JSON contracts, safe discovery, or
  controlled comparisons of equivalent workflows.
- Python developers who want direct access to the small synchronous SDK or CLI.
- Teams that need file and volume workflows inside Modal workspaces.

## Product Priorities

1. Make the plugin the easiest path to a successful agent sandbox run.
2. Keep default discovery and tests resource-free.
3. Require explicit authorization and authentication before live work.
4. Make persistence explicit through volumes.
5. Keep command and file behavior predictable for agents.
6. Preserve a small, compatible SDK and CLI execution surface.
7. Make workflow comparisons reproducible and explicit about their limits.
