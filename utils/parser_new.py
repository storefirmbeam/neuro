#--- Refactored: test_parser.py ---

import re
import uuid
import hashlib
from typing import List, Dict, Union, Optional
from rich.console import Console
from rich.table import Table

class LogicalStep:
    def __init__(self, content: str, language: Optional[str] = None, filename: Optional[str] = None, execute: bool = False):
        self.id = str(uuid.uuid4())
        self.content = content.strip()
        self.language = language or detect_language(content)
        self.filename = filename
        self.execute = execute
        self.hash = hashlib.sha256(self.content.encode()).hexdigest()

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "language": self.language,
            "filename": self.filename,
            "execute": self.execute
        }

def detect_language(code: str) -> str:
    if "import" in code and "def" in code:
        return "python"
    elif "#!/bin/bash" in code or re.search(r"\\b(?:sudo|apt|cd|ls|rm|mv|touch|python|bash)\\b", code):
        return "bash"
    elif "<html>" in code:
        return "html"
    return "unknown"


def parse_ai_response(response: str) -> List[Dict[str, Union[str, None]]]:
    code_blocks = re.findall(r"```(?:([\w+-]+)?\n)?(.*?)```", response, re.DOTALL)
    instructions = response.splitlines()

    steps = []
    filenames = re.findall(r"(?:save|create).+?`([^`]+)`", response, re.IGNORECASE)
    exec_hints = re.findall(r"(?:run|execute).+?`?([^`\n]+)`?", response, re.IGNORECASE)

    file_idx = 0
    for lang, code in code_blocks:
        code = code.strip()
        language = lang if lang else detect_language(code)

        # Ignore non-executable code blocks (like outputs)
        if language == "unknown" or language == "output":
            continue  # Skip this block entirely

        filename = None

        # Look inside code block for a comment like '# hello_requests.py'
        inline_name_match = re.search(r"#\s*(\w+\.(py|sh|bash))", code)
        if inline_name_match:
            filename = inline_name_match.group(1)
        elif file_idx < len(filenames):
            filename = filenames[file_idx]
            file_idx += 1


        matched_exec = any(filename and filename in e for e in exec_hints)

        if language == "bash":
            if any(kw in code.lower() for kw in ["python", "bash", "./", "apt", "pip", "make"]):
                matched_exec = True

        steps.append(LogicalStep(code, language, filename, execute=matched_exec))

    # fallback for single-step execution
    if len(steps) == 1 and steps[0].language in ["python", "bash"]:
        steps[0].execute = True

    # Rich Output
    console = Console()
    table = Table(title="Logical Steps", show_lines=True)
    table.add_column("Lang", style="magenta")
    table.add_column("File", style="green")
    table.add_column("Execute", style="cyan")
    table.add_column("Content", style="white")

    for step in steps:
        table.add_row(step.language, str(step.filename), str(step.execute), step.content)

    console.print(table)
    return [step.to_dict() for step in steps]