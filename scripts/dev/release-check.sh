#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "==> plugin and skill contract"
uv run pytest \
  tests/test_packaging.py::test_modal_sandbox_plugin_identity_and_marketplace_contract \
  tests/test_packaging.py::test_public_skill_encodes_cli_prerequisite_and_safe_workflows \
  tests/test_packaging.py::test_plugin_distributes_portable_scripts_examples_and_evals \
  tests/test_plugin_scripts.py::test_workflow_examples_validate_without_modal \
  tests/test_plugin_scripts.py::test_evaluator_enforces_metrics_and_live_boundary

echo "==> deterministic plugin evaluation"
uv run python plugins/modal-sandbox/scripts/evaluate.py \
  docs/generated/plugin-skill-forward-test-predictions.json >/dev/null

echo "==> official plugin and skill validators when installed"
plugin_validator="${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py"
skill_validator="${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py"
if [[ -f "$plugin_validator" ]]; then
  uv run python "$plugin_validator" plugins/modal-sandbox
else
  echo "Official plugin validator unavailable; repository contract tests remain authoritative in CI."
fi
if [[ -f "$skill_validator" ]]; then
  uv run python "$skill_validator" plugins/modal-sandbox/skills/modal-sandbox
else
  echo "Official skill validator unavailable; repository contract tests remain authoritative in CI."
fi

echo "==> build"
uv build --clear

echo "==> twine check"
uv run twine check dist/*

echo "==> installed wheel smoke"
tmpdir="$(mktemp -d)"
python_bin="$(command -v python || command -v python3)"
uv venv "$tmpdir/venv" --python "$python_bin"
venv_python="$tmpdir/venv/bin/python"
venv_sandbox="$tmpdir/venv/bin/sandbox"
if [[ ! -x "$venv_python" ]]; then
  venv_python="$tmpdir/venv/Scripts/python.exe"
  venv_sandbox="$tmpdir/venv/Scripts/sandbox.exe"
fi
uv pip install --python "$venv_python" dist/*.whl
"$venv_python" -c "import sandbox, sandbox_cli; assert sandbox.Sandbox; assert sandbox_cli"
"$venv_sandbox" schema >/dev/null

echo "==> repository-independent plugin smoke"
(
  cd "$tmpdir"
  # Full portability tests cover workflow compatibility and scripts/preflight.py.
  "$venv_python" "$OLDPWD/plugins/modal-sandbox/scripts/benchmark.py" \
    "$OLDPWD/plugins/modal-sandbox/examples/python-json-workflow.json" \
    --validate-only >/dev/null
  "$venv_python" "$OLDPWD/plugins/modal-sandbox/scripts/workflow.py" \
    "$OLDPWD/plugins/modal-sandbox/examples/run-tests-safely.json" \
    --validate-only >/dev/null
  "$venv_python" "$OLDPWD/plugins/modal-sandbox/scripts/evaluate.py" \
    "$OLDPWD/docs/generated/plugin-skill-forward-test-predictions.json" >/dev/null
)

echo "Release readiness check passed."
