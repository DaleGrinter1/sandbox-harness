#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ "${MODAL_SANDBOX_SDK_RUN_MODAL_TESTS:-}" != "1" ]]; then
  echo "Live Modal tests are opt-in because they create real Modal resources."
  echo "Run with MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 when you intend to use Modal."
  exit 2
fi

uv run pytest tests/test_modal_live.py
