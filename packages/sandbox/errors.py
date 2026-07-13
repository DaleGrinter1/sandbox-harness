"""Exception types raised by the sandbox SDK."""

from __future__ import annotations


class SandboxError(RuntimeError):
    """Base exception for SDK-level sandbox failures."""


class ModalAuthenticationError(SandboxError):
    """Raised when Modal credentials are missing, invalid, or expired."""


class SandboxProviderError(SandboxError):
    """Raised when the sandbox provider reports an unexpected failure."""


class SandboxNotFoundError(SandboxProviderError):
    """Raised when a requested running sandbox cannot be found."""


class SandboxTimeoutError(SandboxProviderError):
    """Raised when a provider operation times out before completing."""


class SandboxPermissionError(SandboxProviderError):
    """Raised when a provider operation is denied by permissions or policy."""


class SandboxFilesystemError(SandboxProviderError):
    """Raised when provider-backed sandbox filesystem operations fail."""


class SandboxConflictError(SandboxProviderError):
    """Raised when provider state conflicts with the requested operation."""


class SandboxConfigurationError(SandboxError, ValueError):
    """Raised when sandbox options are invalid or internally inconsistent."""
