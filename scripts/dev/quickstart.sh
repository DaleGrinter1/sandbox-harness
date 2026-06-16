#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "==> Inspecting CLI schema without creating Modal resources"
uv run sandbox schema >/dev/null

echo "==> Checking local Modal setup without creating Modal resources"
uv run sandbox doctor

echo "==> Previewing the first live command without creating Modal resources"
uv run sandbox quickstart

echo "No Modal resources were created."
