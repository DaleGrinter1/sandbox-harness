# Cognitive Load

This repo treats cognitive load as a maintenance constraint, especially for
agent handoff. Prefer changes that make the next reader hold fewer unrelated
ideas in working memory.

## Local Rules

- Keep public modules small enough to scan, but avoid many shallow modules that
  only rename one line of logic.
- Extract helpers when they gather a coherent concern such as validation,
  provider error translation, or metadata adaptation.
- Prefer specific SDK exceptions over generic provider failures when callers can
  make a better decision from the type.
- Keep Modal imported lazily even when extracting provider helpers.
- Do not hide nonzero sandbox command exits behind exceptions; command process
  status belongs in `CommandResult`.

## Current Guidance

The high-level SDK facade should read as user workflow. Private helper modules
should hold validation and provider translation details. The Modal provider may
stay larger than leaf modules when splitting would make Modal behavior harder to
trace.

External note: <https://minds.md/zakirullin/cognitive>
