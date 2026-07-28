# Next Usability Evaluation

This note ranks possible convenience features after the senior-review
remediation work. The goal is to promote only one future initiative at a time,
based on repeated workflow friction rather than surface-area appetite.

## Current Recommendation

Status, cleanup assistance, resource-free preview, and basic `sandbox.toml`
project config have been promoted and implemented. The next candidate should
be evaluated from real usage after those workflows settle rather than added
immediately.

The most plausible next item is bounded local project upload/run, but only if
source seeding, volumes, and project config still leave repeated user friction.

## Candidate Ranking

| Candidate | Value | Safety | Compatibility Cost | Maintenance Cost | Decision |
| --- | --- | --- | --- | --- | --- |
| Status and cleanup assistance | High | High | Medium | Medium | Implemented in `cli-plugin-experience`. |
| Project config profiles | Medium | Medium | Medium | Medium | Basic `sandbox.toml` implemented; richer profiles deferred. |
| Bounded local project upload/run | Medium | Medium | High | High | Defer until source seeding and volume workflows prove insufficient. |
| Async SDK | Low | Medium | High | High | Defer until concrete async callers appear. |
| Generic provider abstraction | Low | Low | High | High | Defer; it conflicts with the Modal-first product boundary. |

## Acceptance Bar For Any Future Candidate

- It must preserve resource-free discovery by default.
- It must expose a JSON-first CLI contract before live execution.
- It must document lifecycle and cleanup behavior.
- It must update parser, schema, generated docs, plugin guidance, and tests
  together.
- It must not require secrets in source files, command history, manifests, or
  generated docs.
