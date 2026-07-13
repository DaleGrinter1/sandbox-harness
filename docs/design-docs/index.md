# Design Docs Index

Design docs are the durable explanation layer for agents and humans. Keep them concise, linked, and grounded in current code.

## Core Docs

- [Core Beliefs](core-beliefs.md): operating principles for this SDK.
- [Cognitive Load](cognitive-load.md): maintainability rules for keeping SDK and agent handoff complexity low.
- [Vercel Compatibility](vercel-style-sdk-compatibility.md): compatibility surface and limits.

## Maintenance Rules

- Prefer updating a design doc when a decision changes behavior.
- Link product specs and exec plans instead of duplicating long context.
- Mark stale or superseded docs clearly and move completed plan records to `docs/exec-plans/completed/`.
