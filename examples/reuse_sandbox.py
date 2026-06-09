from __future__ import annotations

from sandbox import Sandbox


def main() -> None:
    sb = Sandbox.create(runtime="python3.13", sandbox_timeout=600)
    try:
        print(f"reusable sandbox: {sb.sandbox_id}")
        sb.write_text("hello.py", "print('hello from a reusable sandbox')\n")
        print(sb.run("python hello.py").stdout, end="")
        sb.detach()
    except Exception:
        sb.terminate()
        raise


if __name__ == "__main__":
    main()
