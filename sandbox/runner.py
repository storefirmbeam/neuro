# Executes base64-encoded Python from env CODE_B64 with basic guards
from src.tools import *  # triggers registration
import os, base64, io, sys, contextlib, builtins, ast

CODE_B64 = os.environ.get("CODE_B64", "")
src = base64.b64decode(CODE_B64).decode("utf-8", "replace")

# --- AST gate: allow only safe imports/names
ALLOWED_IMPORTS = {"math", "random", "statistics"}
BANNED = {
    "os","sys","subprocess","shutil","pathlib","socket","ctypes","multiprocessing",
    "open","exec","eval","compile","__import__","input","help","dir","vars","locals",
    "globals","getattr","setattr","delattr","exit","quit","breakpoint"
}
tree = ast.parse(src, filename="<tool_code>")
class Gate(ast.NodeVisitor):
    def visit_Import(self, node):
        for n in node.names:
            if n.name.split(".")[0] not in ALLOWED_IMPORTS:
                raise RuntimeError(f"Blocked import: {n.name}")
    def visit_ImportFrom(self, node):
        root = (node.module or "").split(".")[0]
        if root not in ALLOWED_IMPORTS:
            raise RuntimeError(f"Blocked import-from: {node.module}")
    def visit_Name(self, node):
        if node.id in BANNED:
            raise RuntimeError(f"Blocked name: {node.id}")
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in BANNED:
            raise RuntimeError(f"Blocked call to: {node.func.id}")
        self.generic_visit(node)
Gate().visit(tree)

# --- Restricted builtins/import
safe_builtins = {k:v for k,v in builtins.__dict__.items() if k not in BANNED}
_real_import = builtins.__import__
def _safe_import(name, *args, **kwargs):
    root = name.split(".")[0]
    if root not in ALLOWED_IMPORTS:
        raise ImportError(f"Import '{name}' is not allowed")
    return _real_import(name, *args, **kwargs)
safe_builtins["__import__"] = _safe_import

# Preload approved modules
import math, random, statistics  # noqa
g = {"__builtins__": safe_builtins, "math": math, "random": random, "statistics": statistics}

buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf):
        exec(src, g, None)
    out = buf.getvalue().strip()
    print(out if out else "[no output]")
except Exception as e:
    print(f"[sandbox error] {type(e).__name__}: {e}")
