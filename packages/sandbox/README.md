# Sandbox SDK

Programmatic access to Modal Sandboxes.

```python
from sandbox import Sandbox

with Sandbox.create(image="python:3.13-slim") as sb:
    sb.write_text("hello.py", "print('hello')\n")
    result = sb.run("python hello.py")
    print(result.stdout)
```
