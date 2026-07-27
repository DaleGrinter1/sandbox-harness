# PLAN_sandbox-workflow-expansion

## Purpose / Big Picture

Expand the `modal-sandbox` plugin from a coding-task-specific entry point into
the preferred tool for any task that benefits from isolated, reproducible,
resource-controlled execution. Add plugin-owned scripts for deterministic
preflight and workflow benchmarking, and prove that the plugin and its CLI
engine can be installed and used from a clean environment with no repository
checkout.

The finished product should let a user ask Codex to compare representative
company workflows—such as build, test, data-processing, browser automation, or
agent evaluation workflows—under consistent sandbox conditions and receive
structured, comparable results.

## Surprises & Discoveries

- The public skill and plugin metadata currently say “coding tasks,” even
  though the CLI already supports the broader primitive: isolated command and
  file workflows.
- The plugin currently contains only Markdown skill guidance and interface
  metadata. Repository scripts are maintainer-oriented and are not distributed
  with the plugin.
- Public onboarding already separates distribution correctly: the plugin is
  installed from a GitHub marketplace and the execution engine from PyPI via
  `uv tool install`. The remaining gap is an automated clean-environment
  acceptance test, not a need to copy the Python CLI into the plugin.
- Benchmarking company workflows needs an explicit scenario contract and
  result schema. Free-form timing alone would produce results that are neither
  reproducible nor meaningfully comparable.

## Decision Log

- 2026-07-27: Keep `modal-sandbox-sdk` and the `sandbox` CLI as the only runtime
  implementation. Plugin scripts may orchestrate the CLI but must not duplicate
  provider, lifecycle, command, or file-transfer logic.
- 2026-07-27: Broaden discovery language from “coding tasks” to “tasks that need
  isolated, reproducible, or resource-controlled execution,” while retaining
  concrete examples so the skill remains easy to trigger.
- 2026-07-27: Treat workflow benchmarking as comparison of user-supplied or
  fixture-based scenarios under a declared environment, rather than as a claim
  to benchmark entire companies.
- 2026-07-27: Use cross-platform Python for distributed plugin helpers. Shell
  scripts remain appropriate for repository maintenance but are not the
  portable plugin interface.
- 2026-07-27: Require clean-environment acceptance on Linux, macOS, and Windows
  where CI support is available. No acceptance path may rely on the repository
  working directory, `uv run`, or undeclared local files.

## Outcomes & Retrospective

The plugin now describes sandbox needs rather than only coding tasks, with
examples spanning untrusted commands, data workflows, services, agent
evaluations, persistent files, and controlled workflow comparisons. A
14-prompt adversarial corpus and checked-in review record show the candidate
description selecting all ten sandbox-relevant or safe-discovery cases and
rejecting all four local/explanatory cases, with no live action authorized by
planning, destructive, or unauthenticated prompts.

The plugin distributes standard-library `preflight.py` and `benchmark.py`
helpers. The benchmark contract supports bounded warmups and repetitions,
runtime or image selection, resource and network controls, setup and cleanup,
redaction, output hashes and previews, partial results, and distinct failure
classes. Validate-only execution needs neither the CLI nor credentials.

Local Windows validation copied the plugin to a temporary installation and ran
it from an unrelated directory. Release validation also installed the built
wheel into a fresh virtual environment and ran plugin preflight against that
installed CLI outside the checkout. CI now runs the same portability suite on
Linux, macOS, and Windows.

## Context and Orientation

- `ARCHITECTURE.md`
- `docs/PRODUCT_SENSE.md`
- `docs/product-specs/public-plugin-onboarding.md`
- `plugins/modal-sandbox/.codex-plugin/plugin.json`
- `plugins/modal-sandbox/skills/modal-sandbox/SKILL.md`
- `packages/sandbox_cli/cli.py`
- `tests/test_plugin_acceptance.py`
- `tests/test_packaging.py`
- `scripts/dev/release-check.sh`

## Plan of Work

Phase 1 defines the product contract before changing trigger text. Inventory
the sandbox properties that distinguish this product—process isolation,
reproducible runtime selection, bounded lifecycle, network controls, persistent
volumes, and structured JSON results—and turn them into broad but discriminating
skill language. Build an adversarial prompt set that includes coding and
non-coding sandbox needs, near-misses that should not trigger the skill, and
requests that must remain resource-free. Evaluate the current and proposed
descriptions with the target Codex model and retain the smallest wording that
improves recall without causing broad false positives.

Phase 2 specifies workflow benchmarking. Define a versioned scenario manifest
with setup, command, environment, repetitions, timeout, cleanup, and
redaction/output-limit fields. Define a result envelope containing scenario
identity, runtime configuration, warmup and measured runs, duration, exit
status, timeout/truncation state, and failure classification. Start with
repository-owned, credential-free fixtures representing several workflow
shapes; do not encode proprietary company processes or claim cross-company
comparability without equivalent inputs and controls.

Phase 3 adds a thin `plugins/modal-sandbox/scripts/` orchestration layer. Provide
a portable preflight helper and a benchmark runner that call the installed
`sandbox` command, parse its JSON, enforce schema compatibility, and always
attempt cleanup. Keep live execution behind the existing authorization
boundary. Update the skill to invoke these scripts for repeatable procedures
and fall back to documented CLI commands when scripts cannot run.

Phase 4 hardens distribution. Test the GitHub marketplace install and the PyPI
CLI install from temporary, repository-independent environments. Resolve all
plugin assets relative to the installed plugin root, avoid `uv run`, and
document required host tools and supported operating systems. Add CI packaging
checks proving all referenced scripts ship in the plugin and a manual fresh
Codex-thread acceptance check for actual skill discovery.

Phase 5 performs adversarial and release validation. Run static contracts,
creator validators, unit tests with a fake CLI, clean-environment installation
tests, and the full resource-free repository checks. Run any live Modal
benchmark smoke test only when explicitly authorized, with a small budget and
guaranteed cleanup.

## Concrete Steps

1. Add a product spec for general sandbox task selection and workflow
   benchmarking, including non-goals, scenario schema, result schema, safety
   boundary, and acceptance examples.
2. Create a labeled adversarial prompt corpus covering true positives, false
   positives, ambiguous prompts, auth failures, destructive requests, and
   planning-only requests; record the target Codex model/version and evaluation
   rubric with every run.
3. Revise the descriptions in the skill frontmatter, `openai.yaml`, plugin
   manifest, README, and product-sense docs from coding-specific language to
   sandbox-need language. Keep representative coding, data, service, and
   workflow-evaluation examples.
4. Add `plugins/modal-sandbox/scripts/preflight.py` to locate and validate the
   installed CLI, run resource-free discovery, and emit one stable JSON result.
5. Add `plugins/modal-sandbox/scripts/benchmark.py` to validate scenario
   manifests, execute controlled repetitions through the CLI, capture
   structured measurements, redact bounded outputs, and clean up resources.
6. Add credential-free benchmark fixtures and tests using a fake `sandbox`
   executable. Cover success, nonzero command results, timeouts, malformed
   JSON, incompatible schema, partial runs, and cleanup failure.
7. Update the skill with script-first workflows, relative asset resolution,
   explicit live-action rules, and a direct-CLI fallback. Do not let a helper
   install packages, change credentials, or create resources during preflight.
8. Extend packaging and release checks to validate script presence,
   executability through Python, manifest references, absence of repository-only
   paths, and plugin validation.
9. Add clean-environment tests that install the released CLI into an isolated
   tool environment, fetch/install the plugin from its remote marketplace
   source, change to an unrelated temporary directory, and run preflight plus
   fake/no-resource benchmark validation on each supported OS.
10. Perform a fresh Codex-thread adversarial review with the target model.
    Compare trigger precision/recall against the baseline corpus and inspect
    whether the model selects scripts, respects planning-only boundaries, and
    explains live resource creation.
11. Run focused tests, creator validators, `./scripts/dev/check.sh`,
    `./scripts/dev/release-check.sh`, and `./scripts/execplan/check.sh`. Record
    exact evidence in state files before marking any feature complete.

## Machine State

Implementation state is stored beside this plan:

- `state/feature-list.json`
- `state/session-state.json`
- `state/progress.jsonl`

## Progress

Implementation and resource-free release validation completed on 2026-07-27.
Detailed evidence is recorded in `state/progress.jsonl`.

## Testing Approach

Default validation is entirely resource-free. Script tests inject a fake
`sandbox` executable and assert JSON requests, results, authorization
boundaries, output bounds, and cleanup behavior. Packaging tests operate from
an unrelated temporary directory. A CI matrix covers supported host operating
systems. Adversarial skill evaluation uses a versioned labeled prompt corpus
and reports precision, recall, unsafe-action count, and correct workflow
selection.

A minimal live Modal smoke test is opt-in, requires explicit authorization, and
must use unique resource names, strict timeouts, bounded repetitions, and
cleanup in a `finally` path.

## Constraints & Considerations

- Do not broaden the product into a general sandbox platform; Modal remains the
  backend and the SDK/CLI remain deliberately small.
- “Company workflow benchmarking” means controlled comparison of equivalent
  workflow definitions. Results must disclose runtime, region where known,
  image, dependency/cache state, repetitions, and limitations.
- Do not run untrusted or proprietary workflow inputs without explicit user
  authorization and appropriate secrets/network controls.
- Plugin scripts are orchestration and ergonomics, not a second CLI.
- Preserve JSON-first behavior and CLI schema compatibility.
- Installation and upgrades remain user-authorized.
- Default tests must not create Modal resources.
