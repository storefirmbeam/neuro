# utils/parsers.py (patched to treat bash blocks as run commands only)
import re
from typing import List, Dict

def parse_ai_response(message: str) -> List[Dict]:
    steps = []
    seen = set()
    created_files = set()
    default_file_counter = 1
    current_filename = None

    # Match any file definition context
    defined_files = re.findall(r"create (?:a|an)?\s*file named `?(\w+\.\w+)`?", message, re.IGNORECASE)
    if defined_files:
        current_filename = defined_files[-1].strip()

    # Match fenced code blocks with language hints
    matches = re.findall(r"```(\w+)?\n(.*?)```", message, re.DOTALL)
    for lang, content in matches:
        lang = lang.strip().lower() if lang else "text"
        content = content.strip()

        # Ignore URLs or pure text output
        if lang == "text" and content.startswith("http"):
            continue

        if lang == "python":
            filename = current_filename or f"code{default_file_counter}.py"
            step = {"type": "create_file", "name": filename, "language": lang, "content": content}
            key = (step["type"], step["name"], step["content"])
            if key not in seen:
                steps.append(step)
                seen.add(key)
            created_files.add(filename)
            default_file_counter += 1

        elif lang == "bash":
            # Treat each bash line as its own run_command
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and re.match(r'^[a-zA-Z]', line):
                    step = {"type": "run_command", "language": "bash", "command": line}
                    key = (step["type"], step["command"])
                    if key not in seen:
                        steps.append(step)
                        seen.add(key)

    # Match inline commands
    valid_starters = (
        "apt", "pip", "pip3", "python", "python3", "bash", "node", "npm", "npx",
        "conda", "ruby", "gem", "java", "javac", "go", "cargo",
        "echo", "cd", "ls", "pwd", "mkdir", "rm", "mv", "cp", "chmod", "chown", "touch", "cat", "head", "tail", "grep", "find",
        "curl", "wget", "ping", "dig", "host", "ifconfig", "ip",
        "git", "make", "cmake", "g++", "gcc", "docker", "docker-compose", "systemctl",
        "flask", "uvicorn", "manage.py"
    )

    inline_cmds = re.findall(r"`([^\n`]+)`", message)
    for cmd in inline_cmds:
        parts = cmd.strip().split()
        if not parts:
            continue

        starter = parts[0]

        if starter == "import":
            continue

        if starter in ("python", "python3") and len(parts) > 1:
            intended_file = parts[1]
            if intended_file not in created_files:
                parts[1] = current_filename or list(created_files)[0] if created_files else "code.py"
                cmd = " ".join(parts)

        if starter in valid_starters:
            step = {"type": "run_command", "language": "bash", "command": cmd.strip()}
            key = (step["type"], step["command"])
            if key not in seen:
                steps.append(step)
                seen.add(key)

    return steps
