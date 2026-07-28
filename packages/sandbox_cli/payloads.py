"""JSON payload builders for sandbox CLI discovery and management commands."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from . import schema as cli_schema
from .auth import modal_setup_commands
from .resources import list_modal_apps, sandbox_apps, stop_modal_app
from .schema import QUICKSTART_COMMAND, RECOMMENDED_FIRST_COMMANDS, SETUP_COMMANDS


@dataclass(frozen=True)
class PayloadServices:
    """Dependency hooks used by payload builders.

    Tests can replace these hooks without patching module globals in this file.
    """

    modal_package_info: Callable[[], dict[str, object]]
    credential_status: Callable[[], dict[str, object]]
    modal_config_path: Callable[[], Path]
    recommended_setup_command: Callable[[], str]
    verify_modal_token: Callable[..., dict[str, object]]


def package_version() -> str:
    """Return the installed package version used by CLI metadata."""
    return cli_schema.package_version()


def safe_quickstart_commands() -> list[str]:
    """Return recommended commands that do not create Modal resources."""
    return cli_schema.safe_quickstart_commands()


def live_quickstart_command() -> str:
    """Return the first live Modal verification command."""
    return cli_schema.live_quickstart_command()


def dry_command_names() -> list[str]:
    """Return dry command names that never create Modal resources."""
    return cli_schema.dry_command_names()


def schema_payload(*, version: str) -> dict[str, object]:
    """Build the machine-readable CLI contract."""
    payload = cli_schema.schema_payload()
    payload["version"] = version
    return payload


def agent_manifest_payload(*, version: str) -> dict[str, object]:
    """Build a compact low-token manifest for coding agents."""
    payload = cli_schema.agent_manifest_payload()
    payload["version"] = version
    return payload


def readiness(
    modal_package: dict[str, object],
    credentials: dict[str, object],
    *,
    recommended_setup_command: str,
) -> dict[str, object]:
    """Summarize whether the local environment looks ready for live sandboxes."""
    problems: list[str] = []
    next_steps: list[str] = []

    if not modal_package["installed"]:
        problems.append("modal_package_not_installed")
        next_steps.append("Install dependencies with `uv sync`.")

    if credentials["status"] == "partial_environment":
        problems.append("modal_credentials_partial_environment")
        next_steps.append("Set both `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`, or run `uv run modal setup`.")
    elif not credentials["complete"]:
        problems.append("modal_credentials_missing")
        next_steps.append(f"Run `{recommended_setup_command}` before creating a live sandbox.")

    ready = not problems
    if ready:
        next_steps.append("Run `sandbox quickstart --run` to create a short-lived sandbox and verify execution.")

    return {
        "ready": ready,
        "status": "ready" if ready else "needs_setup",
        "problems": problems,
        "next_steps": next_steps,
    }


def dry_payload(services: PayloadServices) -> dict[str, object]:
    """Build safe-discovery command metadata without creating resources."""
    modal_package = services.modal_package_info()
    credentials = services.credential_status()
    readiness_payload = readiness(
        modal_package,
        credentials,
        recommended_setup_command=services.recommended_setup_command(),
    )
    return {
        "status": "ready_to_run" if readiness_payload["ready"] else "needs_setup",
        "creates_modal_resources": False,
        "dry_commands": dry_command_names(),
        "safe_commands": safe_quickstart_commands(),
        "recommended_next_command": "sandbox quickstart",
        "live_command": live_quickstart_command(),
        "checks": {
            "ready": readiness_payload["ready"],
            "modal_package": modal_package,
            "credentials": credentials,
            "problems": readiness_payload["problems"],
        },
        "next_steps": readiness_payload["next_steps"],
    }


def status_payload(args: argparse.Namespace) -> dict[str, object]:
    """Build read-only Modal app status metadata."""
    result = list_modal_apps(environment=args.modal_environment, timeout=args.status_timeout)
    apps = result.get("apps", [])
    filtered = sandbox_apps(cast(list[dict[str, object]], apps), app_name=args.app_name)
    selected = filtered if args.all else [app for app in filtered if app.get("name") == args.app_name]
    return {
        "status": "ok" if result["ok"] else "error",
        "creates_modal_resources": False,
        "contacts_modal": True,
        "app_name": args.app_name,
        "environment": args.modal_environment,
        "apps": selected,
        "all_sandbox_apps": filtered if args.all else None,
        "summary": {
            "visible_apps": len(selected),
            "sandbox_apps": len(filtered),
            "next_cleanup_command": f"sandbox cleanup --app {args.app_name} --yes" if selected else None,
        },
        "error": result.get("error"),
    }


def cleanup_payload(args: argparse.Namespace) -> dict[str, object]:
    """Build or execute explicit Modal app cleanup."""
    targets: list[str] = []
    if args.app:
        targets.append(args.app)
    if args.all_sandbox_apps:
        status = list_modal_apps(environment=args.modal_environment, timeout=args.status_timeout)
        if not status.get("ok"):
            return {
                "status": "error",
                "creates_modal_resources": False,
                "contacts_modal": True,
                "stops_modal_resources": False,
                "targets": [],
                "error": status.get("error"),
            }
        targets.extend(
            str(app.get("app_id") or app.get("name"))
            for app in sandbox_apps(cast(list[dict[str, object]], status.get("apps", [])), app_name=args.app_name)
            if app.get("app_id") or app.get("name")
        )
    targets = sorted(set(targets))

    if not targets:
        return {
            "status": "nothing_selected",
            "creates_modal_resources": False,
            "contacts_modal": bool(args.all_sandbox_apps),
            "stops_modal_resources": False,
            "targets": [],
            "next_steps": ["Pass --app APP_ID_OR_NAME --yes, or --all-sandbox-apps --yes."],
        }

    if not args.yes:
        return {
            "status": "dry_run",
            "creates_modal_resources": False,
            "contacts_modal": bool(args.all_sandbox_apps),
            "stops_modal_resources": False,
            "targets": targets,
            "next_steps": ["Rerun with --yes to stop the listed Modal apps."],
        }

    stopped = [
        stop_modal_app(target, environment=args.modal_environment, timeout=args.status_timeout) for target in targets
    ]
    return {
        "status": "stopped" if all(item["ok"] for item in stopped) else "partial_failure",
        "creates_modal_resources": False,
        "contacts_modal": True,
        "stops_modal_resources": True,
        "targets": targets,
        "results": stopped,
    }


def doctor_payload(services: PayloadServices, *, verify: bool = False) -> dict[str, object]:
    """Build local Modal readiness diagnostics without creating resources."""
    modal_package = services.modal_package_info()
    credentials = services.credential_status()
    verification = None
    if verify:
        verification = services.verify_modal_token(command=(sys.executable, "-m", "modal", "token", "info"))
        credentials = {**credentials, **verification}
    readiness_payload = readiness(
        modal_package,
        credentials,
        recommended_setup_command=services.recommended_setup_command(),
    )
    recommended_commands = [*RECOMMENDED_FIRST_COMMANDS]
    if not credentials["complete"]:
        recommended_commands.append(
            {
                "command": services.recommended_setup_command(),
                "creates_modal_resources": False,
                "purpose": "Sign in to Modal when credentials are missing or incomplete.",
            }
        )
    if credentials["status"] == "partial_environment":
        ready_hint = (
            "Modal token environment variables are incomplete. Set both token variables before creating a sandbox."
        )
    elif not credentials["complete"]:
        ready_hint = "Complete Modal credentials were not found. Run modal setup before creating a sandbox."
    elif verify and not credentials["verified"]:
        ready_hint = "Modal credentials are complete locally, but verification failed."
    elif verify:
        ready_hint = "Modal credentials are complete locally and verified by Modal."
    else:
        ready_hint = "Modal credentials are complete locally. Run `sandbox doctor --verify` to verify them with Modal."

    if readiness_payload["ready"]:
        summary = {
            "ready": True,
            "message": ready_hint,
            "next_command": "sandbox quickstart --run",
        }
    else:
        next_command = services.recommended_setup_command()
        if credentials["status"] == "partial_environment":
            next_command = "Set both MODAL_TOKEN_ID and MODAL_TOKEN_SECRET"
        summary = {
            "ready": False,
            "message": ready_hint,
            "next_command": next_command,
        }

    return {
        **readiness_payload,
        "modal_package": modal_package,
        "credentials": credentials,
        "ready_hint": ready_hint,
        "recommended_commands": recommended_commands,
        "setup_commands": SETUP_COMMANDS,
        "auth_setup_commands": modal_setup_commands(),
        "verification": verification,
        "creates_modal_resources": False,
        "next_safe_command": "sandbox quickstart",
        "summary": summary,
    }


def quickstart_payload(services: PayloadServices, *, creates_modal_resources: bool) -> dict[str, object]:
    """Build quickstart preview or live-run metadata."""
    modal_package = services.modal_package_info()
    credentials = services.credential_status()
    readiness_payload = readiness(
        modal_package,
        credentials,
        recommended_setup_command=services.recommended_setup_command(),
    )
    live_command = live_quickstart_command()
    return {
        "status": "ready_to_run" if readiness_payload["ready"] else "needs_setup",
        "creates_modal_resources": creates_modal_resources,
        "checks": {
            "ready": readiness_payload["ready"],
            "modal_package": modal_package,
            "credentials": credentials,
            "problems": readiness_payload["problems"],
        },
        "next_steps": readiness_payload["next_steps"],
        "safe_commands": safe_quickstart_commands(),
        "live_command": live_command,
        "quickstart_command": QUICKSTART_COMMAND,
    }
