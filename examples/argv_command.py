from __future__ import annotations

from sandbox import Sandbox


def main() -> None:
    with Sandbox.create(runtime="python3.13") as sb:
        result = sb.run_command("python", ["-c", "print(123)"])
        print(result.stdout, end="")


if __name__ == "__main__":
    main()
