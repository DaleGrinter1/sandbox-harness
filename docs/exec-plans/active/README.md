# Active Execution Plans

Each active initiative must be a directory containing exactly:

- one `PLAN_<initiative>.md`
- `state/feature-list.json`
- `state/session-state.json`
- `state/progress.jsonl`

Agents should read the plan first, then the state files in this order:

1. `state/session-state.json`
2. `state/feature-list.json`
3. `state/progress.jsonl`

Markdown task files and `tasks/` directories are deprecated for active initiatives.
