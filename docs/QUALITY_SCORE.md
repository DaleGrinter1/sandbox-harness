# Quality Score

Owner: repository maintainer

Date: 2026-06-25

## Rubric

Score each area from 1 to 5. Any score below 4 should have an action item.

| Area | Score | Evidence | Action Items |
| --- | ---: | --- | --- |
| SDK API clarity | 4 | Focused modules, top-level exports, snapshot/checkpoint naming, and fake-provider tests cover the 0.3 surface. | Keep import compatibility tests current. |
| CLI contract | 4 | JSON schema, golden workflows, CLI tests, generated-schema checks, and bounded watch/source validation cover core commands. | Keep parser, schema, docs, and tests moving together. |
| Modal safety | 4 | Live tests are opt-in; discovery is resource-free; fake tests cover contextual provider failures and Modal-native adapters. | Rerun live acceptance before the 0.3 release. |
| Docs navigation | 4 | README, references, and product specs describe checkpoints, Modal-native snapshots, filesystem inspection, sync, and source seeding. | Keep links updated during doc gardening. |
| Agent handoff | 4 | Exec plans use JSON state and validator. | Append progress entries during long-running work. |

## Expectations

- Review this file before releases.
- Update scores when architecture, docs, or testing posture changes.
- Link action items to active exec-plan features when work is non-trivial.
