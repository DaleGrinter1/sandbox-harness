from __future__ import annotations


class SandboxError(RuntimeError):
    """Base exception for SDK-level sandbox failures."""


class ModalAuthenticationError(SandboxError):
    """Raised when Modal credentials are missing, invalid, or expired."""


class SandboxProviderError(SandboxError):
    """Raised when the sandbox provider reports an unexpected failure."""


class SandboxConfigurationError(SandboxError, ValueError):
    """Raised when sandbox options are invalid or internally inconsistent."""
