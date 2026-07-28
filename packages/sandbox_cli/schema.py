"""Machine-readable CLI schema metadata for modal-sandbox."""

from __future__ import annotations

from importlib import metadata
from typing import Any

from sandbox import Images

SETUP_COMMANDS = [
    "modal setup",
    "python -m modal setup",
    "modal token new",
    "Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in the environment for non-interactive use.",
]

CLI_SCHEMA_VERSION = "1"
QUICKSTART_COMMAND = "python -c 'print(123)'"
DEFAULT_ERROR_NEXT_STEPS = ["Run `sandbox doctor` to inspect local setup without creating Modal resources."]
_USE_ARG_SANDBOX_ID = object()

IMAGE_ALIASES = {
    "py313": Images.PY313,
    "python313": Images.PY313,
    "python-313": Images.PY313,
    "py312": Images.PY312,
    "python312": Images.PY312,
    "python-312": Images.PY312,
    "py311": Images.PY311,
    "python311": Images.PY311,
    "python-311": Images.PY311,
    "ubuntu24": Images.UBUNTU24,
    "ubuntu-24": Images.UBUNTU24,
}

RECOMMENDED_FIRST_COMMANDS = [
    {
        "command": "sandbox dry",
        "creates_modal_resources": False,
        "purpose": "List safe discovery commands before taking action.",
    },
    {
        "command": "sandbox schema",
        "creates_modal_resources": False,
        "purpose": "Inspect the CLI contract before taking action.",
    },
    {
        "command": "sandbox doctor",
        "creates_modal_resources": False,
        "purpose": "Check local Modal package and credential readiness.",
    },
    {
        "command": "sandbox quickstart",
        "creates_modal_resources": False,
        "purpose": "Preview the first live sandbox command.",
    },
    {
        "command": "sandbox quickstart --run",
        "creates_modal_resources": True,
        "purpose": "Create a short-lived Modal Sandbox and run a tiny Python command.",
    },
]

GOLDEN_WORKFLOWS = [
    {
        "id": "safe_first_run",
        "purpose": "Inspect local readiness before creating Modal resources.",
        "creates_modal_resources": False,
        "commands": [
            "sandbox dry",
            "sandbox schema",
            "sandbox doctor",
            "sandbox quickstart",
        ],
        "success_signal": "quickstart reports ready_to_run or gives setup next steps.",
    },
    {
        "id": "short_lived_command",
        "purpose": "Create one short-lived sandbox and verify command execution.",
        "creates_modal_resources": True,
        "commands": [
            "sandbox --image py313 quickstart --run",
            "sandbox --image py313 run \"python -c 'print(123)'\"",
        ],
        "success_signal": "command JSON has exit_code 0 and expected stdout.",
    },
    {
        "id": "persistent_workspace_files",
        "purpose": "Preserve files across separate CLI calls using a Modal workspace volume.",
        "creates_modal_resources": True,
        "commands": [
            'sandbox --image py313 --workspace-volume work write app.py --content "print(123)"',
            'sandbox --image py313 --workspace-volume work run "python app.py"',
            "sandbox --image py313 --workspace-volume work read app.py",
            "sandbox --image py313 --workspace-volume work snapshot",
            "sandbox --image py313 --workspace-volume work sync",
        ],
        "success_signal": "read returns the file content, snapshot names the workspace volume, and sync exits 0.",
    },
    {
        "id": "long_lived_reuse",
        "purpose": "Reuse one live sandbox for iterative work, then terminate it.",
        "creates_modal_resources": True,
        "commands": [
            "sandbox --image py313 --name agent-workspace start",
            'sandbox --sandbox-name agent-workspace write app.py --content "print(123)"',
            'sandbox --sandbox-name agent-workspace run "python app.py"',
            "sandbox --sandbox-name agent-workspace stop",
        ],
        "success_signal": "start returns sandbox_id and sandbox_name; stop returns status terminated.",
    },
]

PATH_RULES = {
    "relative_paths": "Resolved inside the sandbox workspace.",
    "absolute_paths": "Used as absolute paths inside the sandbox.",
    "workspace_escape": "Relative paths using '..' cannot escape the workspace.",
}

LIVE_MODAL_COMMANDS = [
    "quickstart --run",
    "start",
    "stop",
    "run",
    "run-command",
    "write",
    "read",
    "ls",
    "mkdir",
    "rm",
    "upload",
    "download",
    "domain",
    "wait-ready",
    "snapshot",
    "snapshot-filesystem",
    "snapshot-directory",
    "mount-image",
    "unmount-image",
    "stat",
    "watch",
    "sync",
    "seed-git",
    "seed-tarball",
]

RESOURCE_MANAGEMENT_COMMANDS = [
    "status",
    "cleanup --yes",
]

COMMAND_RESULT_SCHEMA = {
    "command": "string",
    "stdout": "string",
    "stderr": "string",
    "exit_code": "integer|null",
    "duration_ms": "integer",
    "timed_out": "boolean",
    "stdout_truncated": "boolean",
    "stderr_truncated": "boolean",
    "max_output_bytes": "integer|null",
}

AGENT_SKILLS = {
    "public_plugin": {
        "path": "plugins/modal-sandbox/skills/modal-sandbox/SKILL.md",
        "purpose": "End-user Codex workflow for safe discovery and authorized Modal Sandbox execution.",
    },
    "repo_understanding": {
        "path": ".agents/skills/modal-sandbox-repo-understanding/SKILL.md",
        "purpose": "Repo orientation, product boundaries, golden workflows, and planning state.",
    },
    "cli_workflows": {
        "path": ".agents/skills/modal-sandbox-cli-workflows/SKILL.md",
        "purpose": "Safe discovery, live Modal command choices, volume workflows, and JSON output interpretation.",
    },
    "package_maintenance": {
        "path": ".agents/skills/modal-sandbox-package-maintenance/SKILL.md",
        "purpose": "SDK, CLI, provider, docs, tests, packaging, and release-facing changes.",
    },
    "understanding_check": {
        "path": ".agents/skills/modal-sandbox-understanding-check/SKILL.md",
        "purpose": "Quiz or coach users on repo architecture, workflows, docs, and validation rules.",
    },
    "modal_upstream": {
        "path": ".agents/skills/modal/SKILL.md",
        "purpose": "Modal-owned SDK guidance when installed; repo-local skills remain source of truth for this package.",
    },
}

COMMANDS_SCHEMA: dict[str, dict[str, Any]] = {
    "start": {
        "summary": "Create a Modal sandbox, print its ID, and leave it running.",
        "creates_sandbox": True,
        "arguments": {},
        "options": {
            "global creation options": "Supports --name, --tag, --image, --runtime, --workspace, --workspace-volume, --volume, --env, network policy, resources, ports, readiness probes, and timeout flags."
        },
        "output": {
            "sandbox_id": "string",
            "status": "started",
            "ready": "boolean when --wait-ready is used",
            "workspace": "string",
            "sandbox_timeout": "integer",
            "use_command": "string",
            "stop_command": "string",
        },
        "example": "sandbox --image python:3.13-slim --name agent-workspace start",
    },
    "stop": {
        "summary": "Terminate a running Modal sandbox by ID or name.",
        "creates_sandbox": False,
        "arguments": {"sandbox_id": "Modal sandbox object ID. Can also be passed with --sandbox-id."},
        "options": {"global --sandbox-name": "Terminate a running named sandbox."},
        "output": {"sandbox_id": "string|null", "sandbox_name": "string|null", "status": "terminated"},
        "example": "sandbox stop sb-abc123",
    },
    "status": {
        "summary": "List Modal apps visible to this sandbox project without creating resources.",
        "creates_sandbox": False,
        "contacts_modal": True,
        "arguments": {},
        "options": {
            "--all": "Show all visible apps that look owned by modal-sandbox.",
            "--modal-environment ENV": "Modal environment passed to `modal app list`.",
            "--timeout SECONDS": "Maximum seconds to wait for Modal app listing.",
        },
        "output": {
            "status": "ok|error",
            "creates_modal_resources": "false",
            "contacts_modal": "true",
            "apps": "object[]",
            "summary": "object",
            "error": "string|null",
        },
        "example": "sandbox status",
    },
    "cleanup": {
        "summary": "Preview or stop selected Modal sandbox apps.",
        "creates_sandbox": False,
        "contacts_modal": "only with --all-sandbox-apps or --yes",
        "arguments": {},
        "options": {
            "--app APP_ID_OR_NAME": "Modal app ID or name to stop.",
            "--all-sandbox-apps": "Target every visible modal-sandbox app.",
            "--yes": "Actually stop selected Modal apps. Omit for dry-run JSON.",
            "--modal-environment ENV": "Modal environment passed to Modal app commands.",
            "--timeout SECONDS": "Maximum seconds to wait for Modal app commands.",
        },
        "output": {
            "status": "nothing_selected|dry_run|stopped|partial_failure",
            "creates_modal_resources": "false",
            "stops_modal_resources": "boolean",
            "targets": "string[]",
            "results": "object[] when --yes is used",
        },
        "example": "sandbox cleanup --app modal-sandbox-sdk --yes",
    },
    "run": {
        "summary": "Run a shell command inside a Modal sandbox.",
        "creates_sandbox": True,
        "arguments": {"command": "Shell command string to run."},
        "options": {
            "--cwd": "Working directory inside the sandbox. Relative paths resolve inside the workspace.",
            "--use-command-exit-code": "Return the sandbox command exit code as the CLI exit code.",
            "global --max-output-bytes": "Maximum captured bytes for stdout and stderr separately. Use 0 to capture no bytes.",
        },
        "output": COMMAND_RESULT_SCHEMA,
        "example": "sandbox --image python:3.13-slim run \"python -c 'print(123)'\"",
    },
    "run-command": {
        "summary": "Run an argv-style command without shell wrapping.",
        "creates_sandbox": True,
        "arguments": {
            "cmd": "Executable to run.",
            "args": "Arguments passed to the executable without shell parsing.",
        },
        "options": {
            "--cwd": "Working directory inside the sandbox. Relative paths resolve inside the workspace.",
            "--env KEY=VALUE": "Per-command environment variable. Repeatable.",
            "--use-command-exit-code": "Return the sandbox command exit code as the CLI exit code.",
            "global --max-output-bytes": "Maximum captured bytes for stdout and stderr separately. Use 0 to capture no bytes.",
        },
        "output": COMMAND_RESULT_SCHEMA,
        "example": "sandbox --runtime python3.13 run-command python -c 'print(123)'",
    },
    "write": {
        "summary": "Write a file inside the sandbox workspace.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {
            "--content": "Inline UTF-8 text content to write.",
            "--content-file": "Local UTF-8 text file to read and write.",
            "--stdin": "Read UTF-8 text from standard input.",
            "--binary-file": "Local binary file to read and write as bytes.",
            "--binary-stdin": "Read raw bytes from standard input and write as binary.",
        },
        "output": {"path": "string", "status": "wrote"},
        "example": 'sandbox --workspace-volume work write hello.py --content "print(123)"',
    },
    "read": {
        "summary": "Read UTF-8 text from a file inside the sandbox workspace.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {},
        "output": {"path": "string", "content": "string"},
        "example": "sandbox --workspace-volume work read hello.py",
    },
    "ls": {
        "summary": "List direct children of a sandbox directory.",
        "creates_sandbox": True,
        "arguments": {"path": "Directory path. Defaults to '.'."},
        "options": {},
        "output": {"path": "string", "files": "string[]"},
        "example": "sandbox --workspace-volume work ls .",
    },
    "mkdir": {
        "summary": "Create a directory inside the sandbox workspace.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {"--no-parents": "Do not create missing parent directories."},
        "output": {"path": "string", "parents": "boolean", "status": "created"},
        "example": "sandbox --workspace-volume work mkdir notes",
    },
    "rm": {
        "summary": "Remove a file or directory inside the sandbox workspace.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {"--recursive": "Remove directories recursively."},
        "output": {"path": "string", "recursive": "boolean", "status": "removed"},
        "example": "sandbox --workspace-volume work rm notes --recursive",
    },
    "upload": {
        "summary": "Copy a local file or directory into the sandbox.",
        "creates_sandbox": True,
        "arguments": {
            "local_path": "Path on the local machine.",
            "remote_path": "Relative workspace path or absolute sandbox path.",
        },
        "options": {},
        "output": {"local_path": "string", "remote_path": "string", "status": "uploaded"},
        "example": "sandbox --workspace-volume work upload input.txt input.txt",
    },
    "download": {
        "summary": "Copy a sandbox file or directory to the local machine.",
        "creates_sandbox": True,
        "arguments": {
            "remote_path": "Relative workspace path or absolute sandbox path.",
            "local_path": "Destination path on the local machine.",
        },
        "options": {},
        "output": {"local_path": "string", "remote_path": "string", "status": "downloaded"},
        "example": "sandbox --workspace-volume work download output.txt output.txt",
    },
    "domain": {
        "summary": "Print the public URL for a declared sandbox port.",
        "creates_sandbox": True,
        "arguments": {"port": "Port declared with --encrypted-port or --unencrypted-port at sandbox creation."},
        "options": {"requires --sandbox-id or --sandbox-name": "Attach to a sandbox created with a declared port."},
        "output": {"port": "integer", "url": "string"},
        "example": "sandbox --sandbox-id sb-abc123 domain 3000",
    },
    "wait-ready": {
        "summary": "Wait for an existing sandbox readiness probe to report ready.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {
            "requires --sandbox-id or --sandbox-name": "Attach to a sandbox that was created with a readiness probe.",
            "--timeout": "Maximum seconds to wait for readiness.",
        },
        "output": {"sandbox_id": "string|null", "sandbox_name": "string|null", "status": "ready", "timeout": "integer"},
        "example": "sandbox --sandbox-id sb-abc123 wait-ready --timeout 60",
    },
    "snapshot": {
        "summary": "Create a volume-backed workspace snapshot checkpoint.",
        "creates_sandbox": True,
        "arguments": {},
        "options": {"requires --workspace-volume": "Snapshot checkpoints are backed by the workspace Modal volume."},
        "output": {"name": "string", "kind": "modal_volume", "workspace": "string", "status": "created"},
        "example": "sandbox --workspace-volume work snapshot",
    },
    "snapshot-filesystem": {
        "summary": "Create a Modal-native filesystem image snapshot.",
        "creates_sandbox": True,
        "arguments": {},
        "options": {
            "--timeout": "Maximum seconds to wait for Modal snapshot creation.",
            "--ttl": "Snapshot TTL in seconds. Use --no-ttl for no expiry.",
            "--no-ttl": "Keep the snapshot indefinitely.",
        },
        "output": {"image_id": "string", "kind": "modal_filesystem", "path": "null", "ttl_seconds": "integer|null"},
        "example": "sandbox snapshot-filesystem --ttl 604800",
    },
    "snapshot-directory": {
        "summary": "Create a Modal-native directory image snapshot.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {
            "--timeout": "Maximum seconds to wait for Modal snapshot creation.",
            "--ttl": "Snapshot TTL in seconds. Use --no-ttl for no expiry.",
            "--no-ttl": "Keep the snapshot indefinitely.",
        },
        "output": {"image_id": "string", "kind": "modal_directory", "path": "string", "ttl_seconds": "integer|null"},
        "example": "sandbox snapshot-directory . --ttl 604800",
    },
    "mount-image": {
        "summary": "Mount a Modal image snapshot inside the sandbox.",
        "creates_sandbox": True,
        "arguments": {"path": "Mount path inside the sandbox.", "image_id": "Modal image object ID."},
        "options": {},
        "output": {"path": "string", "image_id": "string", "status": "mounted"},
        "example": "sandbox --sandbox-id sb-abc123 mount-image project im-abc123",
    },
    "unmount-image": {
        "summary": "Unmount a Modal image snapshot from the sandbox.",
        "creates_sandbox": True,
        "arguments": {"path": "Mount path inside the sandbox."},
        "options": {},
        "output": {"path": "string", "status": "unmounted"},
        "example": "sandbox --sandbox-id sb-abc123 unmount-image project",
    },
    "stat": {
        "summary": "Return metadata for a sandbox filesystem path.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {},
        "output": {
            "path": "string",
            "kind": "string",
            "size": "integer|null",
            "permissions": "string|null",
            "modified_time": "string|null",
        },
        "example": "sandbox --workspace-volume work stat app.py",
    },
    "watch": {
        "summary": "Watch a sandbox path for filesystem changes and return bounded JSON events.",
        "creates_sandbox": True,
        "arguments": {"path": "Relative workspace path or absolute sandbox path."},
        "options": {
            "--timeout": "Required timeout in seconds. The CLI consumes events until the timeout elapses.",
            "--recursive": "Watch nested subdirectories.",
            "--event TYPE": "Event type filter. Repeatable.",
        },
        "output": {"path": "string", "events": "object[]", "recursive": "boolean", "timeout": "integer"},
        "example": "sandbox --sandbox-id sb-abc123 watch . --timeout 5",
    },
    "sync": {
        "summary": "Persist workspace-volume changes without waiting for sandbox termination.",
        "creates_sandbox": True,
        "arguments": {},
        "options": {"requires --workspace-volume": "Workspace sync requires a named workspace Modal volume."},
        "output": COMMAND_RESULT_SCHEMA,
        "example": "sandbox --workspace-volume work sync",
    },
    "seed-git": {
        "summary": "Clone a public Git repository into the sandbox.",
        "creates_sandbox": True,
        "arguments": {"url": "Public HTTP(S) Git repository URL."},
        "options": {
            "--dest PATH": "Destination path inside the sandbox. Defaults to the workspace.",
            "--ref REF": "Optional branch or tag.",
            "--depth N": "Clone depth. Use 0 for a full clone.",
        },
        "output": COMMAND_RESULT_SCHEMA,
        "example": "sandbox --workspace-volume work seed-git https://github.com/org/repo.git --dest .",
    },
    "seed-tarball": {
        "summary": "Download and extract a public tarball into the sandbox.",
        "creates_sandbox": True,
        "arguments": {"url": "Public HTTP(S) tarball URL."},
        "options": {
            "--dest PATH": "Destination path inside the sandbox. Defaults to the workspace.",
            "--strip-components N": "Leading archive path components to remove.",
        },
        "output": COMMAND_RESULT_SCHEMA,
        "example": "sandbox --workspace-volume work seed-tarball https://example.com/source.tar.gz",
    },
    "dry": {
        "summary": "List safe discovery commands that do not create Modal resources.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {"global --dry": "Alias for this command when no subcommand is provided."},
        "output": {
            "status": "string",
            "creates_modal_resources": "false",
            "dry_commands": "string[]",
            "safe_commands": "string[]",
            "recommended_next_command": "string",
            "live_command": "string",
            "checks": "object",
            "next_steps": "string[]",
        },
        "example": "sandbox dry",
    },
    "schema": {
        "summary": "Print this machine-readable CLI schema.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {"--agent": "Print a compact agent manifest instead of the full CLI schema."},
        "output": {"schema_version": "string", "commands": "object"},
        "example": "sandbox schema",
    },
    "auth": {
        "summary": "Print supported Modal authentication commands without accepting secrets.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {
            "deprecated --token-id/--token-secret": "Rejected because secrets should not appear in command arguments.",
        },
        "output": {
            "status": "manual_setup_required",
            "message": "string",
            "commands": "string[]",
            "config_path": "string",
            "creates_modal_resources": "false",
        },
        "example": "sandbox auth",
    },
    "preview": {
        "summary": "Preview resolved live behavior without creating resources.",
        "creates_sandbox": False,
        "arguments": {"command": "Live command name to preview.", "args": "Command arguments to display."},
        "options": {"global creation options": "Resolved into redacted preview metadata."},
        "output": {
            "status": "preview",
            "creates_modal_resources": "false",
            "would_create_sandbox": "boolean",
            "would_attach": "boolean",
            "image": "string|null",
            "volumes": "object[]",
            "env": "object",
            "network": "object",
            "resources": "object",
            "lifecycle": "string",
        },
        "example": "sandbox --image py313 --workspace-volume work preview run python app.py",
    },
    "doctor": {
        "summary": "Inspect local Modal package and credential setup, with beginner next steps.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {"--verify": "Run `modal token info` to verify credentials without creating sandbox resources."},
        "output": {
            "ready": "boolean",
            "status": "string",
            "problems": "string[]",
            "next_steps": "string[]",
            "recommended_commands": "object[]",
            "modal_package": "object",
            "credentials": "object",
            "verification": "object|null",
            "setup_commands": "string[]",
            "creates_modal_resources": "false",
            "summary": "object",
        },
        "example": "sandbox doctor",
    },
    "quickstart": {
        "summary": "Preview or run the first beginner sandbox command.",
        "creates_sandbox": False,
        "arguments": {},
        "options": {
            "--run": "Create a short-lived Modal Sandbox and run the quickstart Python command.",
            "global creation options": "With --run, supports --name, --tag, --image, --runtime, --workspace, --workspace-volume, --volume, --env, network policy, resources, ports, and timeout flags.",
        },
        "output": {
            "creates_modal_resources": "boolean",
            "status": "string",
            "checks": "object",
            "safe_commands": "string[]",
            "live_command": "string",
            "quickstart_command": "string",
            "command": "string when --run is used",
            "stdout": "string when --run is used",
            "stderr": "string when --run is used",
            "exit_code": "integer|null when --run is used",
            "duration_ms": "integer when --run is used",
            "timed_out": "boolean when --run is used",
            "stdout_truncated": "boolean when --run is used",
            "stderr_truncated": "boolean when --run is used",
            "max_output_bytes": "integer|null when --run is used",
            "quickstart": "object when --run is used",
        },
        "example": "sandbox quickstart --run",
    },
}


def package_version() -> str:
    """Return the installed package version used by CLI metadata.

    Returns:
        Installed distribution version, or the local development fallback.
    """
    try:
        return metadata.version("modal-sandbox-sdk")
    except metadata.PackageNotFoundError:
        return "dev"


def safe_quickstart_commands() -> list[str]:
    """Return recommended commands that do not create Modal resources."""
    return [command["command"] for command in RECOMMENDED_FIRST_COMMANDS if command["creates_modal_resources"] is False]


def live_quickstart_command() -> str:
    """Return the first live Modal verification command."""
    return "sandbox quickstart --run"


def dry_command_names() -> list[str]:
    """Return dry command names that never create Modal resources."""
    return ["dry", "schema", "doctor", "quickstart"]


def schema_payload() -> dict[str, object]:
    """Build the machine-readable CLI contract.

    Returns:
        JSON-serializable schema containing command metadata, lifecycle notes,
        auth guidance, image aliases, and golden workflows.
    """
    return {
        "name": "sandbox",
        "package": "modal-sandbox-sdk",
        "version": package_version(),
        "schema_version": CLI_SCHEMA_VERSION,
        "description": "CLI for running commands and file workflows inside Modal Sandboxes.",
        "default_output": "json",
        "global_options": {
            "--app-name": "Modal app name used for sandbox creation.",
            "--config": "Project sandbox TOML config path. Defaults to sandbox.toml when present.",
            "--no-config": "Ignore project sandbox config.",
            "--name": "Name assigned to a newly created sandbox. Unique within the app while running.",
            "--tag KEY=VALUE": "Tag assigned to a newly created sandbox. Repeatable.",
            "--workspace": "Default sandbox directory for relative paths.",
            "--image": "Registry image tag or supported alias passed to Modal.",
            "--runtime": "Vercel-style runtime alias. Supported values: python3.13, node24, node22.",
            "--workspace-volume": "Modal volume name mounted at the workspace path.",
            "--volume NAME:/mount": "Modal volume name and absolute sandbox mount path. Repeatable.",
            "--env KEY=VALUE": "Environment variable passed to the sandbox. Repeatable.",
            "--timeout": "Command timeout in seconds for run.",
            "--sandbox-timeout": "Modal sandbox lifetime timeout in seconds.",
            "--cpu": "CPU request passed through to Modal.",
            "--memory": "Memory request in MiB passed through to Modal.",
            "--gpu": "GPU request passed through to Modal.",
            "--region": "Region preference passed through to Modal.",
            "--block-network": "Block outbound network access from the sandbox.",
            "--allow-domain DOMAIN": "Allow sandbox outbound network access to a domain. Repeatable.",
            "--allow-cidr CIDR": "Allow sandbox outbound network access to a CIDR range. Repeatable.",
            "--allow-inbound-cidr CIDR": "Allow inbound tunnel/connect-token access from a CIDR range. Repeatable.",
            "--sandbox-id": "Attach to an existing Modal sandbox by ID instead of creating one.",
            "--sandbox-name": "Attach to an existing running Modal sandbox by name instead of creating one.",
            "--max-output-bytes": "Maximum captured bytes for stdout and stderr separately. Defaults to 10485760; use 0 to capture no bytes.",
            "--encrypted-port": "Expose an HTTPS Modal tunnel for the given port. Repeatable.",
            "--unencrypted-port": "Expose a TCP Modal tunnel for the given port. Repeatable.",
            "--readiness-tcp PORT": "Create a sandbox with a Modal TCP readiness probe.",
            "--readiness-exec COMMAND": "Create a sandbox with a Modal exec readiness probe parsed into argv.",
            "--readiness-interval-ms": "Readiness probe polling interval in milliseconds. Defaults to 100.",
            "--wait-ready": "Wait for readiness before running an operational command.",
            "--ready-timeout": "Maximum seconds to wait when --wait-ready is used. Defaults to 300.",
        },
        "path_rules": PATH_RULES,
        "lifecycle": {
            "creates_or_attaches_per_command": True,
            "dry_commands": dry_command_names(),
            "safe_discovery_commands": dry_command_names(),
            "live_modal_commands": LIVE_MODAL_COMMANDS,
            "long_lived_cli_workflow": "Use start to create a sandbox, --sandbox-id to reuse it, and stop to terminate it.",
            "named_sandboxes": "Use --name NAME when starting a sandbox and --sandbox-name NAME to attach to the currently running named sandbox.",
            "created_sandboxes_close_behavior": "terminate",
            "attached_sandboxes_close_behavior": "detach",
            "persistent_files": "Use --workspace-volume to preserve files across separate CLI commands.",
            "volume_mounts": "Use --volume NAME:/mount to mount additional Modal volumes at absolute sandbox paths.",
            "domain_allowlist": "Use --allow-domain DOMAIN to restrict sandbox outbound network access to listed domains.",
            "cidr_allowlists": "Use --allow-cidr CIDR for outbound IP ranges and --allow-inbound-cidr CIDR for inbound tunnel/connect-token ranges.",
            "project_config": "Values from sandbox.toml fill omitted global options; explicit CLI flags win.",
            "resource_management_commands": RESOURCE_MANAGEMENT_COMMANDS,
            "preflight_validation": "Invalid lifecycle combinations and global configuration are rejected before sandbox creation.",
        },
        "auth": {
            "requires_modal_credentials": True,
            "setup_commands": SETUP_COMMANDS,
            "environment_variables": ["MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "MODAL_PROFILE"],
            "token_acquisition": {
                "url": "https://modal.com/settings/tokens",
                "description": (
                    "Create a token at the Modal dashboard, then set MODAL_TOKEN_ID and "
                    "MODAL_TOKEN_SECRET for non-interactive use. For local setup, use "
                    "Modal's supported `modal setup` or `modal token set` commands."
                ),
                "non_interactive_command": "Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in the environment.",
                "local_token_command": "modal token set",
            },
        },
        "image_aliases": IMAGE_ALIASES,
        "recommended_first_commands": RECOMMENDED_FIRST_COMMANDS,
        "golden_workflows": GOLDEN_WORKFLOWS,
        "commands": COMMANDS_SCHEMA,
    }


def agent_manifest_payload() -> dict[str, object]:
    """Build a compact low-token manifest for coding agents.

    Returns:
        JSON-serializable agent orientation data. This intentionally omits the
        full command schema; agents can call `sandbox schema` when they need
        command-level detail.
    """
    return {
        "name": "sandbox-agent-manifest",
        "package": "modal-sandbox-sdk",
        "version": package_version(),
        "schema_version": CLI_SCHEMA_VERSION,
        "description": "Low-token orientation manifest for the modal-sandbox plugin and its SDK/CLI engine.",
        "product_boundary": [
            "Codex plugin and end-user skill backed by a small Python SDK and JSON-first CLI.",
            "The plugin requires the installed sandbox CLI and does not duplicate it or add MCP.",
            "Not a generic sandbox platform or replacement for Modal's full SDK.",
            "Keep Modal imported lazily and default validation resource-free.",
        ],
        "read_order": [
            "AGENTS.md",
            "ARCHITECTURE.md",
            "docs/PRODUCT_SENSE.md",
            "docs/references/cli.md",
            "docs/exec-plans/index.md",
        ],
        "skills": AGENT_SKILLS,
        "safe_discovery": {
            "creates_modal_resources": False,
            "commands": [
                "sandbox dry",
                "sandbox schema --agent",
                "sandbox schema",
                "sandbox doctor",
                "sandbox quickstart",
            ],
        },
        "live_modal": {
            "requires_explicit_user_request": True,
            "opt_in_test_command": "MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 ./scripts/dev/live-smoke.sh",
            "commands": LIVE_MODAL_COMMANDS,
        },
        "resource_management": {
            "status_command": "sandbox status",
            "cleanup_preview": "sandbox cleanup --app APP_ID_OR_NAME",
            "cleanup_execute": "sandbox cleanup --app APP_ID_OR_NAME --yes",
            "cleanup_requires_explicit_user_request": True,
        },
        "project_config": {
            "filename": "sandbox.toml",
            "rule": "Config fills omitted global options; explicit CLI flags win.",
            "disable": "sandbox --no-config ...",
        },
        "golden_workflows": GOLDEN_WORKFLOWS,
        "path_rules": PATH_RULES,
        "validation": {
            "quick_no_resource": "./scripts/dev/quickstart.sh",
            "full_no_resource": "./scripts/dev/check.sh",
            "schema_codegen": "./scripts/dev/schema.sh",
            "exec_plan_state": "./scripts/execplan/check.sh",
            "live_modal": "MODAL_SANDBOX_SDK_RUN_MODAL_TESTS=1 ./scripts/dev/live-smoke.sh",
        },
        "planning": {
            "index": "docs/exec-plans/index.md",
            "active_plan_rule": "If active initiatives exist, read their PLAN file and JSON/JSONL state before editing.",
            "completed_plan_rule": "Do not read completed plan state unless doing archaeology or release retrospective work.",
        },
        "docs": {
            "agent_notes": "docs/references/agents.md",
            "new_agent_prompt": "docs/references/new-agent-prompt.md",
            "cli_reference": "docs/references/cli.md",
            "quality": "docs/QUALITY_SCORE.md",
            "reliability": "docs/RELIABILITY.md",
            "security": "docs/SECURITY.md",
        },
    }
