from __future__ import annotations

from sandbox import Sandbox


def main() -> None:
    with Sandbox.create(runtime="node24", encrypted_ports=[3000], sandbox_timeout=600) as sb:
        sb.write_text(
            "server.mjs",
            (
                "import http from 'node:http';\n"
                "http.createServer((_, res) => res.end('hello from Modal\\n'))"
                ".listen(3000, '0.0.0.0');\n"
            ),
        )
        sb.run_command_detached("node", ["server.mjs"])
        print(sb.domain(3000))


if __name__ == "__main__":
    main()
