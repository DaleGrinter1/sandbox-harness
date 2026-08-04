#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ "${MODAL_SANDBOX_PLUGIN_RUN_MODAL_TESTS:-}" != "1" ]]; then
  echo "The plugin live smoke is opt-in because it creates and contacts real Modal resources."
  echo "Run with MODAL_SANDBOX_PLUGIN_RUN_MODAL_TESTS=1 only when you authorize that work."
  exit 2
fi

smoke_app="modal-sandbox-plugin-smoke-$(date -u +%Y%m%d-%H%M%S)-$$"
smoke_tmpdir="$(mktemp -d)"
result_file="$smoke_tmpdir/result.json"
cleanup_file="$smoke_tmpdir/cleanup.json"
sandbox_bin="$(uv run python -c 'import shutil; print(shutil.which("sandbox") or "")')"

if [[ -z "$sandbox_bin" ]]; then
  echo "Could not resolve the sandbox CLI from the project environment." >&2
  exit 1
fi

cleanup() {
  "$sandbox_bin" cleanup --app "$smoke_app" --yes >"$cleanup_file" 2>/dev/null || true
  rm -rf "$smoke_tmpdir"
}
trap cleanup EXIT

echo "==> resource-free distributed preflight"
uv run python plugins/modal-sandbox/scripts/preflight.py \
  --sandbox-executable "$sandbox_bin" >/dev/null

echo "==> resource-free preview"
"$sandbox_bin" --app-name "$smoke_app" \
  preview run python -c "print('modal-sandbox-plugin-smoke-ok')" >/dev/null

echo "==> authorized short-lived command"
"$sandbox_bin" --app-name "$smoke_app" \
  run "python -c \"print('modal-sandbox-plugin-smoke-ok')\"" >"$result_file"

uv run python -c \
  'import json,sys; p=json.load(open(sys.argv[1], encoding="utf-8")); assert p["exit_code"] == 0; assert "modal-sandbox-plugin-smoke-ok" in p["stdout"]' \
  "$result_file"

echo "==> explicit cleanup and verification"
"$sandbox_bin" cleanup --app "$smoke_app" --yes >"$cleanup_file"
uv run python -c \
  'import json,sys; p=json.load(open(sys.argv[1], encoding="utf-8")); assert p["status"] == "stopped"; assert p["stops_modal_resources"] is True' \
  "$cleanup_file"
"$sandbox_bin" --app-name "$smoke_app" status >/dev/null

trap - EXIT
rm -rf "$smoke_tmpdir"
echo "Plugin live smoke passed and cleanup completed."
