"""Common registry image presets for Modal sandboxes."""

from __future__ import annotations


_PY313 = "python:3.13-slim"
_PY312 = "python:3.12-slim"
_PY311 = "python:3.11-slim"
_UBUNTU24 = "ubuntu:24.04"

PY313 = _PY313
PY312 = _PY312
PY311 = _PY311
UBUNTU24 = _UBUNTU24

PYTHON_313_SLIM = _PY313
PYTHON_312_SLIM = _PY312
PYTHON_311_SLIM = _PY311
UBUNTU_2404 = _UBUNTU24

__all__ = [
    "Images",
    "PY313",
    "PY312",
    "PY311",
    "UBUNTU24",
    "PYTHON_313_SLIM",
    "PYTHON_312_SLIM",
    "PYTHON_311_SLIM",
    "UBUNTU_2404",
]


class Images:
    """Named image presets for common sandbox base images.

    These constants are plain registry tags, so they behave the same as passing
    the string directly to `Sandbox.create(image=...)`.
    """

    PY313 = _PY313
    PY312 = _PY312
    PY311 = _PY311
    UBUNTU24 = _UBUNTU24

    # Backward-compatible aliases for callers who prefer explicit names.
    PYTHON_313_SLIM = _PY313
    PYTHON_312_SLIM = _PY312
    PYTHON_311_SLIM = _PY311
    UBUNTU_2404 = _UBUNTU24
