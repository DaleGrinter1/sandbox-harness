# Product Sense

`modal-sandbox-sdk` helps developers and coding agents run short-lived or
reusable Modal Sandboxes from Python and shell scripts. It is a lightweight
helper around common Modal Sandbox workflows, not a replacement for Modal's
backend or full SDK.

## Target Users

- Python developers who want a small synchronous SDK for Modal Sandboxes.
- Coding agents that need JSON CLI contracts and safe discovery commands.
- Teams that need file and volume workflows inside Modal workspaces.

## Product Priorities

1. Make the first successful sandbox run easy.
2. Keep default discovery and tests resource-free.
3. Make persistence explicit through volumes.
4. Keep command and file behavior predictable for agents.
5. Preserve a small public API.
6. Add Modal-native helpers only when they clarify common workflows.
