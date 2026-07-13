"""Modal provider exception translation helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import NoReturn

from .errors import (
    ModalAuthenticationError,
    SandboxFilesystemError,
    SandboxPermissionError,
    SandboxProviderError,
    SandboxTimeoutError,
)

_TRANSIENT_ERROR_KEYWORDS = frozenset(
    ["connection", "timeout", "network", "unavailable", "retry", "reset", "refused", "temporary"]
)
_FILESYSTEM_CONTEXT_KEYWORDS = frozenset(
    [
        "copying",
        "creating directory",
        "listing files",
        "reading",
        "removing",
        "stating",
        "watching",
        "writing",
    ]
)

MODAL_AUTH_GUIDANCE = """Modal authentication is required to use Modal sandboxes.

Run one of these commands to sign in:
  modal setup
  python -m modal setup

For non-interactive environments, configure a Modal token instead:
  modal token new

You can also provide credentials with MODAL_TOKEN_ID and MODAL_TOKEN_SECRET.
After setup completes, retry your sandbox command."""


def is_transient_error(exc: Exception) -> bool:
    """Return whether an exception looks transient enough to retry."""
    return any(keyword in str(exc).lower() for keyword in _TRANSIENT_ERROR_KEYWORDS)


def is_modal_auth_error(
    exc: Exception,
    modal: object | None = None,
    *,
    load_modal: Callable[[], object] | None = None,
) -> bool:
    """Return whether an exception is Modal's configured auth error type."""
    if modal is None and load_modal is not None:
        try:
            modal = load_modal()
        except RuntimeError:
            return False

    auth_error = getattr(getattr(modal, "exception", None), "AuthError", None)
    return isinstance(exc, auth_error) if isinstance(auth_error, type) else False


def raise_with_auth_guidance(exc: Exception) -> None:
    """Raise a package auth error with actionable Modal setup guidance."""
    detail = str(exc).strip()
    message = MODAL_AUTH_GUIDANCE
    if detail:
        message = f"{message}\n\nModal error: {detail}"
    raise ModalAuthenticationError(message) from exc


def translate_modal_auth_error(
    exc: Exception,
    modal: object | None = None,
    *,
    load_modal: Callable[[], object] | None = None,
) -> None:
    """Translate Modal auth failures into SDK-specific exceptions."""
    if is_modal_auth_error(exc, modal, load_modal=load_modal):
        raise_with_auth_guidance(exc)


def is_modal_not_found_error(
    exc: Exception,
    modal: object | None = None,
    *,
    load_modal: Callable[[], object] | None = None,
) -> bool:
    """Return whether an exception is Modal's not-found error type."""
    if modal is None and load_modal is not None:
        try:
            modal = load_modal()
        except RuntimeError:
            return False

    not_found_error = getattr(getattr(modal, "exception", None), "NotFoundError", None)
    return isinstance(exc, not_found_error) if isinstance(not_found_error, type) else False


def raise_provider_error(exc: Exception, *, context: str | None = None) -> NoReturn:
    """Raise a provider error with optional operation context."""
    detail = str(exc) or exc.__class__.__name__
    if context:
        detail = f"{context}: {detail}"

    error_type: type[SandboxProviderError]
    if isinstance(exc, TimeoutError):
        error_type = SandboxTimeoutError
    elif isinstance(exc, PermissionError):
        error_type = SandboxPermissionError
    elif context and any(keyword in context for keyword in _FILESYSTEM_CONTEXT_KEYWORDS):
        error_type = SandboxFilesystemError
    else:
        error_type = SandboxProviderError
    raise error_type(detail) from exc
