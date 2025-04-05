# sandbox.py (final patched)
import subprocess
import uuid
import os
import re
from typing import List, Dict

def run_steps_in_docker(steps: List[Dict], base_image="neuro_base", verbose=False) -> str:
    session_id = uuid.uuid4().hex[:6]
    container_name = f"neuro_sandbox_{session_id}"
    temp_dir = f"/tmp/neuro/{session_id}"
    os.makedirs(temp_dir, exist_ok=True)

    bash_script_path = os.path.join(temp_dir, "launch.sh")
    all_bash_lines = []
    created_files = []

    with open(bash_script_path, "w") as script:
        script.write("#!/bin/bash\nset -e\n")

        for step in steps:
            if step["type"] == "create_file":
                fpath = os.path.join(temp_dir, step["name"])
                with open(fpath, "w") as f:
                    f.write(step["content"])
                created_files.append(step["name"])
                script.write(f"echo '[📝] Creating file {step['name']}'\n")

            elif step["type"] == "run_command":
                cmd = step["command"].strip()
                if cmd and not cmd.startswith("-"):
                    if cmd.startswith("curl "):
                        continue
                    if cmd.startswith("python "):
                        parts = cmd.split()
                        if len(parts) == 2 and parts[1] not in created_files:
                            py_files = [f for f in created_files if f.endswith(".py")]
                            if py_files:
                                cmd = f"python {py_files[0]}"
                    script.write(f"echo '[💻] Running: {cmd}'\n")
                    script.write(cmd + "\n")


            elif step["type"] == "run_code":
                lang = step["language"]
                ext = "py" if lang == "python" else lang
                fname = f"code.{ext}"
                fpath = os.path.join(temp_dir, fname)
                with open(fpath, "w") as f:
                    f.write(step["code"])
                created_files.append(fname)
                script.write(f"echo '[🚀] Executing {fname}'\n")
                if lang == "python":
                    script.write(f"python /app/{fname}\n")
                elif lang == "bash":
                    script.write(f"bash /app/{fname}\n")
                else:
                    script.write(f"echo '⚠️ Unsupported language: {lang}'\n")

        # Append all combined execution commands
        #script.writelines([line + "\n" for line in all_bash_lines])

    os.chmod(bash_script_path, 0o755)

    try:
        result = subprocess.run([
            "docker", "run", "--rm",
            "-v", f"{temp_dir}:/app",
            "--name", container_name,
            base_image,
            "/bin/bash", "/app/launch.sh"
        ], capture_output=True, text=True, timeout=120)

        output = result.stdout + result.stderr

        # Show curl lines as hints
        curl_cmds = [step["command"] for step in steps if step["type"] == "run_command" and step["command"].startswith("curl ")]
        if curl_cmds:
            output += "\n💡 Test manually:\n"
            for curl in curl_cmds:
                output += f"   {curl}\n"

        if verbose:
            print("\n[🔍 VERBOSE MODE ENABLED]\n")
            print(output)

        return output

    except subprocess.TimeoutExpired:
        return "⏰ Code execution timed out."
    except FileNotFoundError:
        return "🐳 Docker is not installed or not in PATH."
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"
