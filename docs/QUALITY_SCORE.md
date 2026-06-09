# Quality Score

Owner: repository maintainer

Date: 2026-06-09

## Rubric

Score each area from 1 to 5. Any score below 4 should have an action item.

| Area | Score | Evidence | Action Items |
| --- | ---: | --- | --- |
| SDK API clarity | 4 | Focused modules and top-level exports. | Keep import compatibility tests current. |
| CLI contract | 4 | JSON schema, golden workflows, and CLI tests cover core commands. | Add schema drift check to CI if needed. |
| Modal safety | 4 | Live tests are opt-in; discovery is resource-free; fake tests cover contextual provider failures. | Run live acceptance before release when credentials are available. |
| Docs navigation | 4 | Harness-style docs scaffold exists. | Keep links updated during doc gardening. |
| Agent handoff | 4 | Exec plans use JSON state and validator. | Append progress entries during long-running work. |

## Expectations

- Review this file before releases.
- Update scores when architecture, docs, or testing posture changes.
- Link action items to active exec-plan features when work is non-trivial.
