from __future__ import annotations

from typing import cast

from sandbox_cli import schema


def test_schema_auth_guidance_does_not_teach_secret_arguments() -> None:
    payload = schema.schema_payload()
    auth = cast(dict[str, object], payload["auth"])
    commands = cast(dict[str, dict[str, object]], payload["commands"])
    token_acquisition = cast(dict[str, object], auth["token_acquisition"])

    assert "sandbox auth --token-id" not in str(auth)
    assert "sandbox auth --token-id" not in str(commands["auth"])
    assert token_acquisition["non_interactive_command"] == (
        "Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in the environment."
    )


def test_schema_includes_resource_free_preview_command() -> None:
    commands = cast(dict[str, dict[str, object]], schema.schema_payload()["commands"])
    preview = commands["preview"]
    output = cast(dict[str, object], preview["output"])

    assert preview["creates_sandbox"] is False
    assert "without creating resources" in cast(str, preview["summary"])
    assert output["env"] == "object"


def test_schema_includes_status_cleanup_and_config_contracts() -> None:
    payload = schema.schema_payload()
    commands = cast(dict[str, dict[str, object]], payload["commands"])
    lifecycle = cast(dict[str, object], payload["lifecycle"])
    global_options = cast(dict[str, object], payload["global_options"])

    assert commands["status"]["creates_sandbox"] is False
    assert commands["cleanup"]["creates_sandbox"] is False
    assert (
        lifecycle["project_config"] == "Values from sandbox.toml fill omitted global options; explicit CLI flags win."
    )
    assert lifecycle["resource_management_commands"] == ["status", "cleanup --yes"]
    assert "--config" in global_options
