#!/usr/bin/env python3
"""Replace a local plugin version suffix with one Codex cachebuster."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path


def with_cachebuster(version: str, cachebuster: str) -> str:
    base_version = version.split("+", 1)[0]
    sanitized = re.sub(r"[^a-z0-9-]+", "-", cachebuster.strip().lower())
    sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
    if not sanitized:
        raise ValueError("cachebuster must contain at least one letter or digit")
    return f"{base_version}+codex.{sanitized}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugin_path", type=Path)
    parser.add_argument("--cachebuster")
    args = parser.parse_args()

    manifest_path = args.plugin_path.resolve() / ".codex-plugin" / "plugin.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = payload.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError(f"{manifest_path} must contain a non-empty string version")

    token = args.cachebuster or datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    payload["version"] = with_cachebuster(version, token)
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Updated plugin version: {version} -> {payload['version']}")


if __name__ == "__main__":
    main()
