from sandbox import Images, Sandbox

with Sandbox.create(image=Images.PY313) as sandbox:
    sandbox.write_text("hello.py", "print('hello from a Modal Sandbox')\n")
    result = sandbox.run("python hello.py")
    print(result.stdout, end="")
