# Tech Debt Tracker

Track known technical debt that is not yet large enough to become an active execution plan.

| Area | Debt | Impact | Proposed Trigger |
| --- | --- | --- | --- |
| Live Modal validation | Snapshot semantics should be confirmed with an opt-in live test before release. | Medium | Run live test suite with Modal credentials. |
| Docs gardening | No scheduled automation is available from this repo. | Low | Run weekly manual process from `docs/PLANS.md`. |
