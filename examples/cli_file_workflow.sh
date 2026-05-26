#!/usr/bin/env sh
set -eu

uv run sandbox --image py313 --workspace-volume my-workspace write hello.py --content "print('hello from sandbox')"
uv run sandbox --image py313 --workspace-volume my-workspace run "python hello.py"
uv run sandbox --image py313 --workspace-volume my-workspace read hello.py
