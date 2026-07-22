# Product Sense

`modal-sandbox` helps coding agents run short-lived or reusable Modal
Sandboxes through one Codex skill. The plugin is the product front door and
uses the public `modal-sandbox-sdk` JSON CLI as its execution engine. The
package remains available to developers directly; neither layer replaces
Modal's backend or full SDK.

## Target Users

- Coding agents that need isolated execution, JSON contracts, and safe discovery.
- Python developers who want direct access to the small synchronous SDK or CLI.
- Teams that need file and volume workflows inside Modal workspaces.

## Product Priorities

1. Make the plugin the easiest path to a successful agent sandbox run.
2. Keep default discovery and tests resource-free.
3. Require explicit authorization and authentication before live work.
4. Make persistence explicit through volumes.
5. Keep command and file behavior predictable for agents.
6. Preserve a small, compatible SDK and CLI execution surface.
