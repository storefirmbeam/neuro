# sandbox.py
import subprocess
import uuid
import os
import re

def run_code_in_docker(code: str) -> str:
    container_name = f"neuro_sandbox_{uuid.uuid4().hex[:6]}"
    script_name = "script.py"
    temp_dir = "/tmp/neuro"
    os.makedirs(temp_dir, exist_ok=True)
    script_path = os.path.join(temp_dir, script_name)

    with open(script_path, "w") as f:
        f.write(code)

    # 🧠 Detect 3rd party modules (very basic)
    imports = re.findall(r"^\s*import (\w+)", code, re.MULTILINE)
    third_party = [mod for mod in imports if mod not in ("os", "sys", "math", "time", "datetime", "logging", "subprocess")]

    pip_cmd = ""
    if third_party:
        install_str = " ".join(third_party)
        pip_cmd = f"pip install {install_str} && "

    try:
        result = subprocess.run([
            "docker", "run", "--rm",
            "-v", f"{temp_dir}:/app",
            "--name", container_name,
            "python:3.11",
            "bash", "-c", f"{pip_cmd}python /app/{script_name}"
        ], capture_output=True, text=True, timeout=30)

        return result.stdout + result.stderr

    except subprocess.TimeoutExpired:
        return "⏰ Code execution timed out."

    except FileNotFoundError:
        return "🐳 Docker is not installed or not in PATH."

    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"

