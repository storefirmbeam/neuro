#--- Refactored: test_exe.py ---

import subprocess
import uuid
import os
from typing import List, Dict

def run_steps_in_docker(steps: List[Dict], base_image="neuro_base", verbose=False) -> str:
    session_id = uuid.uuid4().hex[:6]
    container_name = f"neuro_sandbox_{session_id}"
    temp_dir = f"/tmp/neuro/{session_id}"
    os.makedirs(temp_dir, exist_ok=True)

    script_path = os.path.join(temp_dir, "launch.sh")

    with open(script_path, "w") as script:
        script.write("""#!/bin/bash
set -e
cd /app
echo "📁 Mounted from: {mount_path}"
""".replace("{mount_path}", temp_dir))

        for step in steps:
            lang = step.get("language")
            ext = {"python": "py", "bash": "sh"}.get(lang, lang)
            fname = step.get("filename") or f"snippet.{ext}"
            fpath = os.path.join(temp_dir, fname)
            with open(fpath, "w") as f:
                f.write(step["content"])

            script.write(f"echo '[💻] Writing {fname}'\n")
            if step.get("execute"):
                script.write(f"echo '[🚀] Executing {fname}'\n")
                if lang == "python":
                    script.write(f"python /app/{fname}\n")
                elif lang == "bash":
                    script.write(f"bash /app/{fname}\n")
                else:
                    script.write(f"echo '⚠️ Unsupported: {lang}'\n")

    os.chmod(script_path, 0o755)

    try:
        result = subprocess.run([
            "docker", "run", "--rm",
            "-v", f"{temp_dir}:/app",
            "--name", container_name,
            base_image,
            "/bin/bash", "/app/launch.sh"
        ], capture_output=True, text=True, timeout=120)

        return result.stdout + result.stderr

    except subprocess.TimeoutExpired:
        return "⏰ Execution timed out."
    except FileNotFoundError:
        return "🐳 Docker not installed."
    except Exception as e:
        return f"❌ {str(e)}"
