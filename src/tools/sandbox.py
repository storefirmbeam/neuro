# src/tools/sandbox.py
import os
import sys
import json
import shlex
import tempfile
import subprocess
from pathlib import Path
from typing import List, Optional, Union
from ..core.registry import register_tool, ToolSpec
from dotenv import load_dotenv

load_dotenv()

# ---------------- Sandbox root discovery ----------------
def _project_root() -> Path:
    # this file: .../src/tools/sandbox.py -> repo root is parents[2]
    return Path(__file__).resolve().parents[2]

def _sandbox_root() -> Path:
    # Allow override; otherwise use <repo>/sandbox
    env = os.getenv("SANDBOX_DIR", "").strip()
    root = Path(env).expanduser() if env else (_project_root() / "sandbox")
    root.mkdir(parents=True, exist_ok=True)
    return root

ROOT = _sandbox_root()

# ---------------- Helpers ----------------
def _to_text(val) -> str:
    """Best-effort: turn whatever the model sent into a string of code/stdin."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, (bytes, bytearray)):
        try:
            return val.decode("utf-8", "replace")
        except Exception:
            return str(val)
    if isinstance(val, dict):
        for k in ("code", "text", "content", "value"):
            if k in val and isinstance(val[k], str):
                return val[k]
        try:
            return json.dumps(val, ensure_ascii=False)
        except Exception:
            return str(val)
    if isinstance(val, list):
        try:
            return "\n".join(_to_text(x) for x in val)
        except Exception:
            return "\n".join(str(x) for x in val)
    return str(val)

def _string_list(vals) -> List[str]:
    if not vals:
        return []
    if isinstance(vals, str):
        try:
            return shlex.split(vals)
        except Exception:
            return [vals]
    if isinstance(vals, (list, tuple)):
        return [str(v) for v in vals]
    return [str(vals)]

def _resolve_dir(rel: Optional[str]) -> Path:
    """Resolve a directory path inside ROOT (sandbox)."""
    if not rel:
        return ROOT
    p = (ROOT / rel.lstrip("/\\")).resolve()
    if not str(p).startswith(str(ROOT)):
        raise ValueError("cwd must be within sandbox root")
    p.mkdir(parents=True, exist_ok=True)
    return p

def _resolve_file(rel: Optional[str], workdir: Path) -> Path:
    """Resolve a file path inside ROOT (sandbox), relative to workdir if provided."""
    if not rel:
        # caller will use a NamedTemporaryFile in workdir
        return workdir
    safe = rel.strip().lstrip("/\\")
    if not safe.endswith(".py"):
        safe += ".py"
    p = (workdir / safe).resolve()
    if not str(p).startswith(str(ROOT)):
        raise ValueError("filename must be within sandbox root")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

# ---------------- Runners ----------------
def code_exec(
    code: Union[str, dict, list],
    language: str = "python",
    args: Union[str, List[str]] = None,
    stdin: Union[str, dict, list] = None,
    filename: Optional[str] = None,
    timeout: int = 20,
    cwd: Optional[str] = None,
):
    """
    Execute a small code snippet locally (Python-only) inside the sandbox dir.
    Returns: {exit_code, stdout, stderr, file, cmd}
    """
    lang = (language or "python").lower().strip()
    if lang not in ("py", "python"):
        return {"error": f"Unsupported language '{language}'. Only 'python' is supported.",
                "supported": ["python"]}

    code_text = _to_text(code).rstrip("\n") + "\n"
    if not code_text.strip():
        return {"error": "Empty code provided."}

    try:
        workdir = _resolve_dir(cwd)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}

    keep_file = False
    try:
        if filename:
            file_path = _resolve_file(filename, workdir)
            file_path.write_text(code_text, encoding="utf-8")
            keep_file = True
        else:
            tf = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, dir=workdir)
            tf.write(code_text)
            tf.flush()
            tf.close()
            file_path = Path(tf.name)

        cmd = [sys.executable, str(file_path)]
        cmd += _string_list(args)

        try:
            run = subprocess.run(
                cmd,
                input=_to_text(stdin).encode("utf-8") if stdin is not None else None,
                cwd=str(workdir),
                capture_output=True,
                timeout=max(1, int(timeout)),
            )
            out = {
                "exit_code": run.returncode,
                "stdout": run.stdout.decode("utf-8", "replace"),
                "stderr": run.stderr.decode("utf-8", "replace"),
                # return path relative to sandbox root
                "file": str(file_path.resolve().relative_to(ROOT)),
                "cmd": cmd,
                "cwd": str(workdir),
                "sandbox_root": str(ROOT),
            }
        except subprocess.TimeoutExpired as e:
            out = {
                "error": "timeout",
                "timeout": timeout,
                "stdout": (e.stdout or b"").decode("utf-8", "replace"),
                "stderr": (e.stderr or b"").decode("utf-8", "replace"),
                "cmd": cmd,
                "cwd": str(workdir),
                "sandbox_root": str(ROOT),
            }
        except Exception as e:
            out = {"error": f"{type(e).__name__}: {e}", "cwd": str(workdir), "sandbox_root": str(ROOT)}
    finally:
        if not keep_file:
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                pass

    return out

def code_write(path: str, content: Union[str, dict, list], cwd: Optional[str] = None):
    try:
        workdir = _resolve_dir(cwd)
        target = _resolve_file(path, workdir)
        target.write_text(_to_text(content), encoding="utf-8")
        return {"status": "ok", "path": str(target.resolve().relative_to(ROOT)), "cwd": str(workdir)}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}

# ---------------- Tool registrations ----------------
register_tool(ToolSpec(
    name="code_exec",
    kind="function",
    description="Execute a small code snippet (Python only) inside a sandbox directory. Returns stdout/stderr/exit_code.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Source code to run."},
            "language": {"type": "string", "enum": ["python"], "default": "python"},
            "args": {"type": ["array", "string"], "items": {"type": "string"}, "description": "Program arguments."},
            "stdin": {"type": ["string", "object", "array"], "items": {"type": "string"}, "description": "Input piped to the program."},
            "filename": {"type": "string", "description": "Optional filename to save as before running (relative to sandbox/cwd)."},
            "timeout": {"type": "integer", "minimum": 1, "maximum": 120, "default": 20},
            "cwd": {"type": "string", "description": "Working directory inside the sandbox (relative path)."}
        },
        "required": ["code"]
    },
    runner=code_exec
))

register_tool(ToolSpec(
    name="code_write",
    kind="function",
    description="Write a file inside the sandbox directory.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path to write (e.g., 'scripts/hello.py')."},
            "content": {"type": ["string", "object", "array"], "items": {"type": "string"}},
            "cwd": {"type": "string", "description": "Working directory inside the sandbox (relative path)."}
        },
        "required": ["path", "content"]
    },
    runner=code_write
))
