from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4.1-nano"


def load_dotenv(path: Path = Path(".env")) -> None:
    """Load simple KEY=VALUE lines from .env without adding a dependency."""
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPEN_API_KEY")
    if not key:
        raise RuntimeError("Set OPENAI_API_KEY in .env or your shell before running this example.")
    return key


def output_text(response: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in response.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                parts.append(str(content.get("text", "")))
    return "".join(parts).strip()


def create_response(
    *,
    key: str,
    model: str,
    user_input: str,
    previous_response_id: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "input": user_input,
        "instructions": "You are a concise, helpful terminal assistant.",
        "max_output_tokens": 300,
    }
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API request failed with HTTP {exc.code}: {detail}") from exc


def main() -> int:
    load_dotenv()
    key = api_key()
    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    previous_response_id: str | None = None

    print(f"OpenAI agent loop using {model}. Type /exit to quit.")
    while True:
        try:
            prompt = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not prompt:
            continue
        if prompt in {"/exit", "/quit"}:
            return 0

        try:
            response = create_response(
                key=key,
                model=model,
                user_input=prompt,
                previous_response_id=previous_response_id,
            )
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            return 1

        previous_response_id = response.get("id")
        print(f"\nAgent> {output_text(response)}")

        usage = response.get("usage")
        if isinstance(usage, dict):
            print(
                "usage: "
                f"{usage.get('input_tokens', 0)} input, "
                f"{usage.get('output_tokens', 0)} output, "
                f"{usage.get('total_tokens', 0)} total tokens"
            )


if __name__ == "__main__":
    raise SystemExit(main())
