"""Authentication discovery helpers for the sandbox CLI."""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path
from typing import Any, cast


def modal_config_path() -> Path:
    """Return the default Modal config path checked by discovery commands."""
    return Path.home() / ".modal.toml"


def modal_setup_commands() -> list[str]:
    """Return supported Modal-owned credential setup commands."""
    return [
        "uv run modal setup",
        "uv run modal token set",
        "Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in the environment.",
    ]


def credential_status(config_path: Path | None = None) -> dict[str, object]:
    """Inspect local Modal credential signals without contacting Modal.

    Args:
        config_path: Optional Modal config path. Tests pass a temporary file.

    Returns:
        JSON-serializable local credential evidence. `verified` is always
        false here because this function does not contact Modal.
    """
    env_has_id = bool(os.environ.get("MODAL_TOKEN_ID"))
    env_has_secret = bool(os.environ.get("MODAL_TOKEN_SECRET"))
    has_complete_env = env_has_id and env_has_secret

    path = config_path or modal_config_path()
    config_exists = path.exists()
    profile = os.environ.get("MODAL_PROFILE") or "default"
    profile_exists = False
    profile_complete = False
    config_error: str | None = None

    if config_exists:
        try:
            with path.open("rb") as f:
                parsed = cast(dict[str, object], tomllib.load(f))
            values = parsed.get(profile)
            if isinstance(values, dict):
                profile_exists = True
                profile_values = cast(dict[str, object], values)
                profile_complete = bool(profile_values.get("token_id")) and bool(profile_values.get("token_secret"))
        except tomllib.TOMLDecodeError as exc:
            config_error = str(exc)
        except OSError as exc:
            config_error = str(exc)

    complete = has_complete_env or profile_complete
    configured = env_has_id or env_has_secret or config_exists

    if has_complete_env:
        status = "complete_from_environment"
    elif env_has_id or env_has_secret:
        status = "partial_environment"
    elif profile_complete:
        status = "complete_from_modal_toml"
    elif config_error is not None:
        status = "unreadable_modal_toml"
    elif config_exists and profile_exists:
        status = "partial_modal_toml_profile"
    elif config_exists:
        status = "modal_toml_without_selected_profile"
    else:
        status = "missing_or_unknown"

    return {
        "status": status,
        "configured": configured,
        "complete": complete,
        "verified": False,
        "verification_performed": False,
        "environment": {
            "modal_token_id_set": env_has_id,
            "modal_token_secret_set": env_has_secret,
            "environment_vars_complete": has_complete_env,
        },
        "modal_toml": {
            "path": str(path),
            "exists": config_exists,
            "profile": profile,
            "profile_exists": profile_exists,
            "profile_complete": profile_complete,
            "error": config_error,
        },
    }


def verify_modal_token(*, command: tuple[str, ...] = ("modal", "token", "info"), timeout: int = 20) -> dict[str, Any]:
    """Ask Modal's CLI to verify the currently selected token.

    Args:
        command: Modal CLI command to execute.
        timeout: Maximum seconds to wait.

    Returns:
        JSON-serializable verification result. Output is intentionally trimmed
        and never includes environment variable values.
    """
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError:
        return {
            "verification_performed": True,
            "verified": False,
            "method": "modal token info",
            "error": "modal_cli_not_found",
            "message": "The `modal` command was not found.",
        }
    except subprocess.TimeoutExpired:
        return {
            "verification_performed": True,
            "verified": False,
            "method": "modal token info",
            "error": "verification_timeout",
            "message": f"`modal token info` did not finish within {timeout} seconds.",
        }

    output = (completed.stdout or completed.stderr).strip()
    return {
        "verification_performed": True,
        "verified": completed.returncode == 0,
        "method": "modal token info",
        "exit_code": completed.returncode,
        "message": output.splitlines()[0] if output else "",
    }
