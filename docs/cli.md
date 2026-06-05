# CLI Workflows

The CLI command is `sandbox`. Commands print JSON except for `--help` and
`--version`. Failures also print a JSON error envelope to stderr.

## Discovery

These commands do not create Modal resources:

```bash
uv run sandbox schema
uv run sandbox doctor
uv run sandbox recipes
uv run sandbox quickstart
```

`sandbox schema` prints command metadata, output shapes, lifecycle notes, path
rules, optional companion MCPs, auth setup commands, and examples as JSON.

`sandbox doctor` reports whether the Modal Python package is importable and
whether credentials appear to be configured through environment variables or
`~/.modal.toml`, plus beginner next steps.

`sandbox recipes` prints beginner workflow recipes as JSON.

`sandbox quickstart` previews a first live command without creating resources.
Use `sandbox quickstart --run` to create a short-lived sandbox and run
`python -c 'print(123)'`.

## Commands

Run a command:

```bash
uv run sandbox --image py313 run "python -c 'print(123)'"
```

By default, `sandbox run` exits with status `0` when the SDK call succeeds,
even if the command inside the sandbox exits nonzero. Use
`--use-command-exit-code` when shell scripts should receive the sandbox
command's exit status:

```bash
uv run sandbox run --use-command-exit-code "python -c 'raise SystemExit(7)'"
```

Use `--max-output-bytes` to change the captured stdout/stderr cap for CLI
commands. The guard truncates each stream independently after command output is
captured; it does not live-stream output.

```bash
uv run sandbox --max-output-bytes 1048576 run "python noisy.py"
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

## Long-Lived Sandboxes

Create a reusable sandbox:

```bash
uv run sandbox --image py313 start
```

The output includes a `sandbox_id`. Reuse it with `--sandbox-id`:

```bash
uv run sandbox --sandbox-id sb-abc123 write hello.py --content "print('hello')"
uv run sandbox --sandbox-id sb-abc123 run "python hello.py"
uv run sandbox --sandbox-id sb-abc123 read hello.py
```

Terminate it when you are done:

```bash
uv run sandbox stop sb-abc123
```
