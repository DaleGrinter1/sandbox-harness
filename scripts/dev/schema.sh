#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "==> Regenerating docs/generated/cli-schema.json"
uv run python -c 'import json; from pathlib import Path; from sandbox_cli import cli; Path("docs/generated/cli-schema.json").write_text(json.dumps(cli._schema_payload(), indent=2, sort_keys=True) + "\n", encoding="utf-8")'

echo "==> Verifying generated schema contract"
uv run pytest tests/test_cli.py -k generated_cli_schema_matches_runtime_contract

echo "CLI schema is current."
