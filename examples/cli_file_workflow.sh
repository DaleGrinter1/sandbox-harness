#!/usr/bin/env sh
set -eu

printf "print('hello from sandbox')\n" | uv run sandbox --image py313 --workspace-volume my-workspace write hello.py --stdin
uv run sandbox --image py313 --workspace-volume my-workspace run "python hello.py"
uv run sandbox --image py313 --workspace-volume my-workspace read hello.py
