#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "==> ruff format check"
uv run ruff format --check .

echo "==> ruff lint"
uv run ruff check .

echo "==> pyright"
uv run pyright

echo "==> pytest"
uv run pytest

echo "==> exec-plan state"
./scripts/execplan/check.sh

echo "==> build"
uv build

echo "==> CLI help"
uv run sandbox --help >/dev/null

echo "==> CLI schema"
uv run sandbox schema >/dev/null

echo "Default non-live validation passed."
