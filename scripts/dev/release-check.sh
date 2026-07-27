#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "==> plugin and skill contract"
uv run pytest tests/test_packaging.py tests/test_plugin_scripts.py tests/test_plugin_distribution.py -k 'plugin or marketplace or public_skill or benchmark or preflight or manifest'

echo "==> build"
uv build --clear

echo "==> twine check"
uv run twine check dist/*

echo "==> installed wheel smoke"
tmpdir="$(mktemp -d)"
python -m venv "$tmpdir/venv"
venv_python="$tmpdir/venv/bin/python"
venv_sandbox="$tmpdir/venv/bin/sandbox"
if [[ ! -x "$venv_python" ]]; then
  venv_python="$tmpdir/venv/Scripts/python.exe"
  venv_sandbox="$tmpdir/venv/Scripts/sandbox.exe"
fi
"$venv_python" -m pip install --upgrade pip
"$venv_python" -m pip install dist/*.whl
"$venv_python" -c "import sandbox, sandbox_cli; assert sandbox.Sandbox; assert sandbox_cli"
"$venv_sandbox" schema >/dev/null

echo "==> repository-independent plugin smoke"
(
  cd "$tmpdir"
  "$venv_python" "$OLDPWD/plugins/modal-sandbox/scripts/preflight.py" \
    --sandbox-executable "$venv_sandbox" >/dev/null
  "$venv_python" "$OLDPWD/plugins/modal-sandbox/scripts/benchmark.py" \
    "$OLDPWD/plugins/modal-sandbox/examples/python-json-workflow.json" \
    --validate-only >/dev/null
)

echo "Release readiness check passed."
