# Tech Debt Tracker

Track known technical debt that is not yet large enough to become an active execution plan.

| Area | Debt | Impact | Proposed Trigger |
| --- | --- | --- | --- |
| Docs gardening | No scheduled automation is available from this repo. | Low | Run weekly manual process from `docs/PLANS.md`. |

## Validation Notes

- 2026-06-16: Live Modal validation passed with `MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_live.py`: `6 passed in 297.88s`. Runtime is acceptable for the opt-in live suite.
