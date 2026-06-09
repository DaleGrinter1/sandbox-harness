# Core Beliefs

## Small And Modal-First

This SDK should stay focused on Modal Sandbox workflows. Avoid broad provider abstractions unless they directly improve Modal usage.

## JSON-First CLI

The CLI is designed for scripts and coding agents. Commands print JSON by default so state can be inspected and chained reliably.

## Workspace Safety

Relative SDK file paths resolve inside the sandbox workspace. Local filesystem access is explicit through upload/download helpers only.

## Opt-In Resources

Default tests and discovery commands do not create real Modal resources. Live Modal workflows must be explicit.

## Repository Knowledge Is Canonical

Agent context, execution plans, architecture, product intent, and progress state live in this repository. External notes should be copied or summarized here before agents rely on them.
