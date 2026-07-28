"""Modal app status and cleanup helpers for the sandbox CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any, cast

SANDBOX_APP_PREFIX = "modal-sandbox"


def _run_modal(arguments: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "modal", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _normalize_apps(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, dict):
        payload_dict = cast(dict[str, object], payload)
        raw_apps: object = payload_dict.get("apps") or payload_dict.get("items") or payload_dict.get("data") or []
    else:
        raw_apps = payload
    if not isinstance(raw_apps, list):
        return []

    apps: list[dict[str, object]] = []
    for raw in cast(list[object], raw_apps):
        if not isinstance(raw, dict):
            continue
        raw_app = cast(dict[str, object], raw)
        app_id = raw_app.get("app_id") or raw_app.get("id") or raw_app.get("object_id")
        name = raw_app.get("name") or raw_app.get("app_name") or raw_app.get("description")
        state = raw_app.get("state") or raw_app.get("status") or raw_app.get("running_status")
        if app_id is None and name is None:
            continue
        apps.append(
            {
                "app_id": str(app_id) if app_id is not None else None,
                "name": str(name) if name is not None else None,
                "state": str(state) if state is not None else "unknown",
                "raw": raw_app,
            }
        )
    return apps


def list_modal_apps(*, environment: str | None = None, timeout: int = 30) -> dict[str, object]:
    """List Modal apps through the supported Modal CLI."""
    arguments = ["app", "list", "--json"]
    if environment:
        arguments.extend(["--env", environment])
    completed = _run_modal(arguments, timeout=timeout)
    if completed.returncode != 0:
        return {
            "ok": False,
            "command": ["python", "-m", "modal", *arguments],
            "error": completed.stderr.strip() or completed.stdout.strip(),
            "apps": [],
        }
    try:
        payload: Any = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "command": ["python", "-m", "modal", *arguments],
            "error": "modal app list --json did not return JSON",
            "apps": [],
        }
    apps = _normalize_apps(payload)
    return {"ok": True, "command": ["python", "-m", "modal", *arguments], "apps": apps}


def sandbox_apps(apps: list[dict[str, object]], *, app_name: str) -> list[dict[str, object]]:
    """Return apps that look owned by this package."""
    candidates: list[dict[str, object]] = []
    for app in apps:
        name = str(app.get("name") or "")
        if name == app_name or name.startswith(SANDBOX_APP_PREFIX):
            candidates.append(app)
    return candidates


def stop_modal_app(identifier: str, *, environment: str | None = None, timeout: int = 60) -> dict[str, object]:
    """Stop one Modal app through the supported Modal CLI."""
    arguments = ["app", "stop", "--yes"]
    if environment:
        arguments.extend(["--env", environment])
    arguments.append(identifier)
    completed = _run_modal(arguments, timeout=timeout)
    return {
        "identifier": identifier,
        "command": ["python", "-m", "modal", *arguments],
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "message": (completed.stdout or completed.stderr).strip(),
    }
