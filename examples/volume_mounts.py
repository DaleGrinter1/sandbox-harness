from __future__ import annotations

from sandbox import Sandbox, SandboxVolume


def main() -> None:
    with Sandbox.create(
        runtime="python3.13",
        volumes=[
            SandboxVolume.workspace("sandbox-example-workspace"),
            SandboxVolume(volume="sandbox-example-cache", mount_path="/cache"),
        ],
    ) as sb:
        sb.write_text("hello.py", "print('hello from a volume-backed workspace')\n")
        result = sb.run_command("python", ["hello.py"])
        print(result.stdout, end="")


if __name__ == "__main__":
    main()
