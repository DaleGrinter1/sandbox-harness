# PLAN_senior-review-remediation-and-usability

## Purpose / Big Picture

Make the repository safer to operate, easier to change, and easier for a new
user to understand before adding more public surface area. The first outcome is
to remove credential and retry behavior that can surprise users. The second is
to make the SDK, provider, CLI, tests, and release records easier to navigate.
Only after those issues are addressed should the project add small,
evidence-backed improvements to discovery and day-to-day sandbox workflows.

Success means a new maintainer can locate each responsibility quickly, machine
consumers receive truthful and stable errors, secrets do not need to appear in
command arguments, retries cannot silently repeat unsafe operations, and users
can preview a live command's resolved behavior before it creates resources.

## Surprises & Discoveries

- The default no-resource suite is healthy: `218 passed, 5 skipped` on
  2026-07-28, and the execution-plan validator passes.
- `sandbox auth` accepts the Modal token secret as a command-line argument and
  the generated schema recommends that form. Command arguments can be retained
  in shell history or exposed to local process inspection.
- `packages/sandbox_cli/cli.py` implements its own `~/.modal.toml` writer. It
  does not perform atomic replacement, explicitly set restrictive permissions,
  or reliably round-trip arbitrary TOML values. Modal 1.5 already provides a
  prompted `modal token set` command.
- `sandbox doctor` reports `credentials.authenticated: true` whenever
  `~/.modal.toml` merely exists. It does not prove that the selected profile is
  complete or that Modal accepts the credentials.
- `ModalSandboxProvider._modal_call` identifies transient failures through
  message substrings and retries both reads and mutating operations. Ambiguous
  failures can therefore repeat writes, removals, mounts, or snapshots.
- The CLI catches most SDK exception subclasses as a generic `runtime_error`,
  even though the SDK exposes configuration, not-found, timeout, permission,
  filesystem, conflict, and provider exception types.
- The recent schema and Modal adapter extractions reduced large-file load, but
  their behavior is mostly exercised indirectly. The central modules remain
  large: `cli.py` is 1,332 lines, `provider_modal.py` is 1,124 lines, and
  `sandbox.py` is 862 lines.
- Release and planning records disagree about the plugin version. The current
  manifest is `0.4.0`, while the changelog and active onboarding plan describe
  plugin `0.2.0`. Package and plugin versions may remain independent, but each
  artifact needs one truthful source of record.
- The active public-plugin-onboarding feature list is fully passing, while its
  session state still waits for one manual fresh-configuration acceptance run.
  The initiative should either record that acceptance and close or clearly
  retain it as an outstanding manual gate.
- `docs/QUALITY_SCORE.md` is dated 2026-06-30 and still describes the 0.3
  surface, while the package version is 0.4.1.

## Decision Log

- 2026-07-28: Treat credential handling and retry semantics as release-blocking
  remediation because they can expose secrets or repeat side effects.
- 2026-07-28: Prefer Modal's supported authentication flow over maintaining a
  second credential-file implementation in this repository.
- 2026-07-28: Preserve a synchronous, Modal-first SDK. Do not add async or
  multi-provider surfaces merely to make the project appear more complete.
- 2026-07-28: Use module responsibility and testability as the refactoring
  criteria. Line counts are warning signals, not targets by themselves.
- 2026-07-28: Build a resource-free execution preview before higher-complexity
  conveniences such as project configuration, bulk project upload, or resource
  inventory.

## Outcomes & Retrospective

The remediation is implemented and validated without creating Modal resources.
`sandbox auth` no longer writes credential files or accepts token secrets as
arguments; it points users at Modal's supported setup commands. `sandbox
doctor` now separates local credential evidence from optional verification and
offers `--verify` through `modal token info`. Provider retries are opt-in per
operation and based on typed transient failures, so mutating filesystem and
snapshot operations are not repeated after ambiguous errors. CLI errors now map
SDK exception subclasses to stable JSON categories.

The repo also gained a resource-free `sandbox preview` command, direct schema
and Modal adapter tests, a bounded strict pyright module group, current quality
evidence, and an evidence-gated note for the next usability initiative.

Live Modal acceptance was not run because the user did not explicitly authorize
live resource creation during this implementation.

## Context and Orientation

Read these paths before implementation:

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/PRODUCT_SENSE.md`
- `docs/design-docs/cognitive-load.md`
- `docs/SECURITY.md`
- `docs/RELIABILITY.md`
- `docs/references/cli.md`
- `packages/sandbox/sandbox.py`
- `packages/sandbox/provider_modal.py`
- `packages/sandbox/_modal_errors.py`
- `packages/sandbox/_modal_adapters.py`
- `packages/sandbox_cli/cli.py`
- `packages/sandbox_cli/schema.py`
- `tests/test_cli.py`
- `tests/test_provider_modal.py`

The active public-plugin-onboarding plan must also be reconciled because its
version evidence and manual acceptance state overlap this work.

## Plan of Work

Phase 1 fixes trust and safety issues. Replace or deprecate the custom
credential writer, remove secret-bearing command examples, make doctor report
configuration evidence truthfully, and offer verification only as an explicit
network operation that creates no Modal resources. Define retry policy by
operation safety and typed provider failures rather than broad message matching.
Map public SDK exception types to stable CLI error categories.

Phase 2 restores repository consistency and strengthens change detection.
Reconcile plugin version records, resolve the completed-but-active onboarding
state, update the quality score to the current surface, and add direct tests for
schema, adapter, error, and retry boundaries. Raise typing strictness
incrementally where it produces useful signal without forcing broad annotation
churn.

Phase 3 lowers maintenance complexity. Keep the public entry points stable
while separating CLI parsing, discovery/auth inspection, command handling, and
process exit orchestration. Clarify the provider protocol boundary and extract
only coherent execution or filesystem concerns whose tests become simpler as a
result. Split very large test files by behavior so failures and ownership are
easy to locate.

Phase 4 adds one high-value, low-risk usability feature: a resource-free
execution preview. A user or agent should be able to see the resolved image,
workspace, volumes, network policy, lifecycle, redacted environment keys, and
whether a command creates or attaches to resources before live execution.

Phase 5 evaluates further product ideas against real workflow friction. Consider
project-level configuration profiles, read-only sandbox status/inventory,
explicit cleanup assistance, and a bounded local-project upload/run workflow.
Do not implement these together. Each candidate needs a short design note,
security/lifecycle analysis, CLI schema sketch, and evidence that it removes
repeated user work. Defer an async SDK and generic provider abstraction unless
concrete users require them.

## Concrete Steps

1. Replace secret-bearing `sandbox auth` guidance with Modal's supported
   prompted authentication flow. Decide whether to deprecate the command or
   retain only a safe compatibility shim.
2. Remove custom TOML mutation or make any unavoidable compatibility path
   atomic, profile-aware, correctly escaped, and permission-tested.
3. Change doctor output to distinguish `configured`, `complete`,
   `verified`, and `verification_performed`; add an explicit verification mode
   that never creates a sandbox.
4. Introduce an operation-aware retry policy. Retry only typed transient
   failures and only operations proven safe to repeat; inject delay behavior so
   tests do not sleep.
5. Map SDK exception subclasses to stable CLI error types and document their
   exit-code contract without changing nonzero sandbox command semantics.
6. Reconcile plugin, changelog, test, and plan versions; finish or explicitly
   defer the onboarding manual acceptance gate; update the quality score.
7. Add direct unit tests for `_modal_adapters.py`, `_modal_errors.py`, and
   `schema.py`, including unsupported Modal capability and malformed metadata
   cases.
8. Move type checking toward `standard` one bounded module group at a time.
   Keep public import compatibility tests and avoid unrelated annotation churn.
9. Refactor CLI and provider responsibilities behind existing public entry
   points. Record before/after dependency direction and delete compatibility
   wrappers once no caller relies on them.
10. Split tests by discovery/auth, parser/preflight, handlers, facade lifecycle,
    provider execution, and provider filesystem concerns.
11. Specify and implement a resource-free execution preview, update parser,
    schema, generated contracts, docs, plugin skill, and tests together.
12. Run a short usability evaluation using the golden workflows. Rank later
    candidates by user time saved, safety, compatibility cost, and maintenance
    cost; promote only the best-supported candidate into its own initiative.

## Machine State

Implementation state is stored beside this plan:

- `state/feature-list.json` is the canonical implementation checklist.
- `state/session-state.json` records the active feature and next action.
- `state/progress.jsonl` is append-only and records evidence-backed checkpoints.

Every implementation feature starts with `"passes": false`.

## Progress

The initial senior review, remediation sequence, implementation, and
resource-free validation are complete. All implementation features in
`state/feature-list.json` are marked passing with evidence.

## Testing Approach

Start each feature with focused, resource-free tests. Credential tests must use
temporary paths and non-secret sentinel values. Retry tests must prove attempt
counts separately for idempotent and mutating operations and must not sleep.
CLI error tests must assert JSON category, exit code, next steps, and absence of
tracebacks or secret values.

Run schema generation whenever parser or machine-readable metadata changes:

```bash
./scripts/dev/schema.sh
uv run pytest tests/test_cli.py tests/test_packaging.py
```

Run SDK/provider tests for boundary changes:

```bash
uv run pytest tests/test_sandbox.py tests/test_provider_modal.py
```

Before each release-facing checkpoint:

```bash
./scripts/dev/check.sh
bash ./scripts/dev/release-check.sh
./scripts/execplan/check.sh
```

Default validation must not create Modal resources. Run
`MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 ./scripts/dev/live-smoke.sh` only after
explicit authorization, and use it before releasing provider-facing changes.

## Constraints & Considerations

- Preserve current public imports and CLI schema compatibility unless a
  deprecation and migration path is documented.
- Keep Modal imported lazily.
- Discovery and execution preview must not create, attach to, or terminate
  Modal resources.
- Authentication verification may contact Modal only when explicitly
  requested and must state that distinction in JSON and help text.
- Never print, log, persist in generated docs, or require secrets in command
  arguments.
- Nonzero sandbox command exits remain `CommandResult.exit_code`; they are not
  provider exceptions.
- Avoid retrying operations with ambiguous side effects.
- Do not mix broad refactoring with public feature work in one change.
- Keep generated CLI schema, parser behavior, docs, plugin guidance, and tests
  synchronized.
- Work with the current uncommitted readability refactor; do not discard it.
