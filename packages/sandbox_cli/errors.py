"""CLI error envelope helpers."""

from __future__ import annotations

from sandbox import (
    ModalAuthenticationError,
    SandboxConfigurationError,
    SandboxError,
    SandboxFilesystemError,
    SandboxNotFoundError,
    SandboxPermissionError,
    SandboxProviderError,
    SandboxTimeoutError,
)
from sandbox.errors import SandboxConflictError

DEFAULT_ERROR_NEXT_STEPS = ["Run `sandbox doctor` to inspect local setup without creating Modal resources."]


def error_type_for_exception(exc: Exception) -> str:
    """Return the stable CLI error category for an exception."""
    if isinstance(exc, ModalAuthenticationError):
        return "modal_authentication_error"
    if isinstance(exc, SandboxConfigurationError):
        return "configuration_error"
    if isinstance(exc, SandboxNotFoundError):
        return "not_found_error"
    if isinstance(exc, SandboxTimeoutError):
        return "timeout_error"
    if isinstance(exc, SandboxPermissionError):
        return "permission_error"
    if isinstance(exc, SandboxFilesystemError):
        return "filesystem_error"
    if isinstance(exc, SandboxConflictError):
        return "conflict_error"
    if isinstance(exc, SandboxProviderError):
        return "provider_error"
    if isinstance(exc, SandboxError):
        return "sandbox_error"
    return "runtime_error"


def next_steps_for_error(error_type: str) -> list[str]:
    """Return concise remediation guidance for a CLI error category."""
    if error_type == "modal_authentication_error":
        return ["Run `sandbox doctor`.", "Run `uv run modal setup` or configure Modal token environment variables."]
    if error_type == "configuration_error":
        return ["Review the command arguments.", "Run `sandbox schema` for supported options."]
    if error_type == "not_found_error":
        return ["Check the sandbox ID or name.", "Use `sandbox start` to create a reusable sandbox."]
    if error_type == "timeout_error":
        return ["Increase the relevant timeout or simplify the operation."]
    if error_type == "permission_error":
        return ["Check Modal credentials, workspace permissions, and network policy."]
    if error_type == "filesystem_error":
        return ["Check the sandbox path.", "Remember relative paths resolve inside the sandbox workspace."]
    return DEFAULT_ERROR_NEXT_STEPS


def error_payload(error_type: str, message: str, exit_code: int) -> dict[str, object]:
    """Build the standard JSON error envelope."""
    return {
        "status": "error",
        "error": {
            "type": error_type,
            "message": message,
            "exit_code": exit_code,
            "next_steps": next_steps_for_error(error_type),
        },
    }
