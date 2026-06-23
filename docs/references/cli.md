# CLI Workflows

The CLI command is `sandbox`. Commands print JSON except for `--help` and
`--version`. Failures also print a JSON error envelope to stderr.

## Discovery / Dry Commands

Dry commands are safe discovery commands. They do not create Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
```

`sandbox schema` prints command metadata, output shapes, lifecycle notes, path
rules, auth setup commands, and examples as JSON.

`sandbox doctor` reports whether the Modal Python package is importable and
whether credentials appear to be configured through environment variables or
`~/.modal.toml`, plus beginner next steps.

`sandbox quickstart` previews a first live command without creating resources.
Use `sandbox quickstart --run` to create a short-lived sandbox and run
`python -c 'print(123)'`.

## Golden Workflows

`sandbox schema` includes a `golden_workflows` array so agents can discover the
same first-run paths documented here.

Dry commands / safe discovery, no Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox quickstart
```

Short-lived execution:

```bash
uv run sandbox --image py313 quickstart --run
uv run sandbox --image py313 run "python -c 'print(123)'"
```

Persistent workspace files:

```bash
uv run sandbox --image py313 --workspace-volume work write app.py --content "print(123)"
uv run sandbox --image py313 --workspace-volume work run "python app.py"
uv run sandbox --image py313 --workspace-volume work read app.py
uv run sandbox --image py313 --workspace-volume work snapshot
```

Long-lived sandbox reuse:

```bash
uv run sandbox --image py313 start
uv run sandbox --sandbox-id sb-abc123 write app.py --content "print(123)"
uv run sandbox --sandbox-id sb-abc123 run "python app.py"
uv run sandbox stop sb-abc123
```

## Commands

Run a command:

```bash
uv run sandbox --image py313 run "python -c 'print(123)'"
```

Use `run-command` when you want argv-style execution without shell wrapping:

```bash
uv run sandbox --runtime python3.13 run-command python -c "print(123)"
```

For `run` and `run-command`, relative `--cwd` values resolve inside the
sandbox workspace. Absolute `--cwd` values are used as-is.

By default, `sandbox run` exits with status `0` when the SDK call succeeds,
even if the command inside the sandbox exits nonzero. Use
`--use-command-exit-code` when shell scripts should receive the sandbox
command's exit status. The same flag works with `run-command`:

```bash
uv run sandbox run --use-command-exit-code "python -c 'raise SystemExit(7)'"
uv run sandbox run-command --use-command-exit-code python -c "raise SystemExit(7)"
```

Use `--max-output-bytes` to change the captured stdout/stderr cap for CLI
commands. The guard truncates each stream independently after command output is
captured; it does not live-stream output. Use `0` to capture no bytes.

```bash
uv run sandbox --max-output-bytes 1048576 run "python noisy.py"
```

Use `--allow-domain` to restrict outbound sandbox network access to specific
domains. Repeat the flag for multiple domains:

```bash
uv run sandbox --allow-domain api.openai.com --allow-domain github.com run "python app.py"
```

Use `--allow-cidr` for outbound IP ranges and `--allow-inbound-cidr` for
inbound tunnel/connect-token access:

```bash
uv run sandbox --allow-cidr 10.0.0.0/8 run "python app.py"
uv run sandbox --encrypted-port 8080 --allow-inbound-cidr 203.0.113.0/24 start
```

`--block-network` cannot be combined with domain or CIDR allowlists.

Mount additional Modal volumes with `--volume NAME:/absolute/path`:

```bash
uv run sandbox --volume cache-volume:/cache run "ls /cache"
uv run sandbox --workspace-volume my-workspace --volume cache-volume:/cache run "ls /workspace /cache"
```

## File Workflows

Run a small file workflow with a persistent workspace volume:

```bash
uv run sandbox --image py313 --workspace-volume my-workspace write game.py --content "print('hello')"
uv run sandbox --image py313 --workspace-volume my-workspace ls .
uv run sandbox --image py313 --workspace-volume my-workspace run --cwd /workspace "python game.py"
uv run sandbox --image py313 --workspace-volume my-workspace read game.py
```

`write` accepts inline text, a local UTF-8 file, or standard input:

```bash
uv run sandbox write game.py --content "print('hello')"
uv run sandbox write game.py --content-file game.py
printf "print('hello')\n" | uv run sandbox write game.py --stdin
```

Copy files in and out:

```bash
uv run sandbox --image py313 --workspace-volume my-workspace upload input.txt input.txt
uv run sandbox --image py313 --workspace-volume my-workspace download output.txt output.txt
```

Create and remove directories:

```bash
uv run sandbox --workspace-volume my-workspace mkdir notes
uv run sandbox --workspace-volume my-workspace rm notes --recursive
```

Create a volume-backed workspace checkpoint:

```bash
uv run sandbox --workspace-volume my-workspace snapshot
```

The snapshot response names the mounted workspace volume that backs the
checkpoint. It does not call Modal's local `Volume.commit()` API. Running
`snapshot` without `--workspace-volume` returns a JSON argument error before
creating a sandbox because there is no persistent workspace volume to name.

## Long-Lived Sandboxes

Create a reusable sandbox. Add `--name` when you want a stable handle that can
be reused while the sandbox is running:

```bash
uv run sandbox --runtime node24 --name agent-workspace --encrypted-port 3000 --volume node-cache:/cache start
```

The output includes a `sandbox_id`. If you provided `--name`, the output also
includes `sandbox_name`, and the generated reuse commands prefer
`--sandbox-name`.

Reuse by name:

```bash
uv run sandbox --sandbox-name agent-workspace write hello.py --content "print('hello')"
uv run sandbox --sandbox-name agent-workspace run "python hello.py"
uv run sandbox --sandbox-name agent-workspace read hello.py
uv run sandbox --sandbox-name agent-workspace domain 3000
```

Reuse by ID:

```bash
uv run sandbox --sandbox-id sb-abc123 write hello.py --content "print('hello')"
uv run sandbox --sandbox-id sb-abc123 run "python hello.py"
uv run sandbox --sandbox-id sb-abc123 read hello.py
uv run sandbox --sandbox-id sb-abc123 domain 3000
```

`domain` requires `--sandbox-id` or `--sandbox-name`; use `start` to create a
reusable sandbox with declared ports before resolving a port URL. Invalid
lifecycle combinations and invalid global configuration are rejected before
creating Modal resources.

Terminate it when you are done:

```bash
uv run sandbox stop sb-abc123
uv run sandbox --sandbox-name agent-workspace stop
```
