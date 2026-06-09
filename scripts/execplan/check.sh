#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
node "$ROOT_DIR/scripts/execplan/validate-state.mjs" "$ROOT_DIR"
