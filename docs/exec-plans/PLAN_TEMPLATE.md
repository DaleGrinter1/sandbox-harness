# PLAN_<initiative>

## Purpose / Big Picture

Explain the outcome in user-visible terms. A new agent should understand why this work exists and what will be true when it is done.

## Surprises & Discoveries

Record unexpected facts learned while reading code, running tests, or implementing changes. Include links to files or commands where useful.

## Decision Log

Append dated decisions with the reason and rejected alternatives.

## Outcomes & Retrospective

When the work finishes, summarize what changed, what was validated, and what should be improved next.

## Context and Orientation

List the repo paths, docs, tests, and commands a new agent should read first.

## Plan of Work

Describe the phases of work in narrative form. Keep this human-readable; do not use this section as the implementation checklist.

## Concrete Steps

List the command-level or file-level steps that are expected. Keep steps durable enough for a future agent to resume.

## Machine State

Implementation state is stored beside this plan:

- `state/feature-list.json` is the canonical implementation checklist.
- Every feature starts with `"passes": false`.
- `state/session-state.json` tracks the active feature, blockers, next action, and handoff rules.
- `state/progress.jsonl` is append-only and records meaningful checkpoints with structured evidence.

Do not create markdown task files or `tasks/` directories for default execution tracking.

## Progress

Summarize major checkpoints here only when useful for readers. The append-only detailed log is `state/progress.jsonl`.

## Testing Approach

Describe the validation strategy, including commands that prove features pass. For this repo, default tests must not create real Modal resources.

## Constraints & Considerations

Document constraints, risks, dependencies, and any rules inherited from `AGENTS.md` or product specs.
