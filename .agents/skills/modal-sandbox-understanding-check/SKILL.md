---
name: modal-sandbox-understanding-check
description: Use when the user wants to be quizzed, coached, or checked on their understanding of this modal-sandbox-sdk repository, including architecture, CLI workflows, provider boundaries, docs, execution plans, or validation rules.
---

# Modal Sandbox Understanding Check

Use this skill when the user asks to test, quiz, review, or improve their
understanding of this repository. Keep the tone collaborative and practical,
like a short technical pairing session.

## Read Order

For broad checks, read:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/PRODUCT_SENSE.md`
4. `docs/references/cli.md`
5. Relevant files in `packages/sandbox/` or `packages/sandbox_cli/`

For planning/governance questions, also read `docs/PLANS.md` and
`docs/exec-plans/index.md`.

## Coaching Workflow

1. Ask what area the user wants to check, unless they already named one.
2. Ask 3-5 focused questions. Prefer one question at a time when the topic is
   new, and a short batch when the user asks for a quiz.
3. After each answer, say what is correct, what is missing, and the smallest
   next concept to clarify.
4. Use repo-specific examples instead of generic Python or CLI trivia.
5. End with a concise recap and one suggested next review area.

## Question Areas

- Product shape: small SDK and JSON-first CLI for Modal Sandbox workflows.
- SDK boundary: `Sandbox` facade delegates side effects to a provider.
- Modal provider: lazy Modal import, create vs attach, auth error translation.
- Commands: shell `run`, argv `run_command`, detached command handles.
- Files: relative paths resolve inside the sandbox workspace.
- Persistence: `SandboxVolume.workspace` and CLI `--workspace-volume`.
- CLI lifecycle: safe discovery, one-shot commands, `start`, `--sandbox-id`,
  and `stop`.
- JSON contract: `sandbox schema`, JSON outputs, and JSON error envelopes.
- Tests: fake-provider defaults and opt-in live Modal tests.
- Docs: architecture, product specs, design docs, and execution-plan state.

## Guardrails

- Do not run live Modal commands as part of a quiz unless the user explicitly
  asks for live execution.
- Do not grade harshly. Treat incomplete answers as useful signal.
- Do not invent behavior from memory; verify against the repo when uncertain.
- Keep questions short enough for the user to answer in a sentence or two.
