"""Lifecycle mixin for `ModalSandboxProvider`."""

from __future__ import annotations

from typing import Any, cast

from ._modal_errors import raise_provider_error, translate_modal_auth_error


class ModalLifecycleMixin:
    """Provide attach/detach, termination, readiness, and tunnel helpers."""

    _sandbox: Any
    _owns_sandbox: bool
    _closed: bool

    @staticmethod
    def _load_modal() -> Any:
        raise NotImplementedError

    def detach(self) -> None:
        """Detach from the Modal sandbox without terminating it."""
        detach = getattr(self._sandbox, "detach", None)
        try:
            if callable(detach):
                detach()
            self._owns_sandbox = False
            self._closed = True
        except Exception as exc:
            translate_modal_auth_error(exc, load_modal=self._load_modal)
            raise_provider_error(exc, context="detaching Modal sandbox")

    def terminate(self, *, wait: bool = True) -> None:
        """Terminate the Modal sandbox."""
        terminate = getattr(self._sandbox, "terminate", None)
        try:
            if callable(terminate):
                terminate(wait=wait)
            self._owns_sandbox = False
            self._closed = True
        except Exception as exc:
            translate_modal_auth_error(exc, load_modal=self._load_modal)
            raise_provider_error(exc, context="terminating Modal sandbox")

    def domain(self, port: int) -> str:
        """Return the public HTTPS URL for a declared sandbox port."""
        try:
            tunnels = self._sandbox.tunnels()
            tunnel = tunnels.get(port)
            if tunnel is None:
                raise ValueError(f"No tunnel is available for port {port}.")
            return str(tunnel.url)
        except Exception as exc:
            if isinstance(exc, ValueError):
                raise
            translate_modal_auth_error(exc, load_modal=self._load_modal)
            raise_provider_error(exc, context=f"resolving tunnel for port {port}")

    def wait_until_ready(self, *, timeout: int = 300) -> None:
        """Wait until the sandbox readiness probe succeeds."""
        cast(Any, self)._modal_call(
            lambda: self._sandbox.wait_until_ready(timeout=timeout),
            context="waiting for Modal sandbox readiness",
            retry=True,
        )

    def close(self) -> None:
        """Terminate or detach from the Modal sandbox according to ownership."""
        if self._closed:
            return
        if self._owns_sandbox:
            self.terminate(wait=True)
        else:
            self.detach()
