#!/usr/bin/env sh
set -eu

uv run sandbox --image py313 --workspace-volume my-workspace write notes.txt --content "persistent content"
uv run sandbox --image py313 --workspace-volume my-workspace ls .
uv run sandbox --image py313 --workspace-volume my-workspace read notes.txt
