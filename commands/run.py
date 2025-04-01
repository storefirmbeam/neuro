# commands/run.py
import re
from rich.panel import Panel
from sandbox import run_code_in_docker
from utils.code import extract_code_from_message

def handle_run(memory, console):
    for m in reversed(memory):
        if m["role"] == "assistant":
            code = extract_code_from_message(m["content"])
            if not code:
                console.print("[red]No code block found to execute.[/]")
                return None

            output = run_code_in_docker(code)
            console.print(Panel.fit(output, title="Execution Output", border_style="green"))
            return output

    console.print("[red]No assistant message with code found.[/]")
    return None