# commands/debug.py
import re
from rich.panel import Panel
from ai_stream import stream_chat
from sandbox import run_code_in_docker
from utils.code import extract_code_from_message

def handle_debug(memory, console, config, last_error_output):
    if not last_error_output:
        console.print("[red]No error found from last run.[/]")
        return None

    for m in reversed(memory):
        if m["role"] == "assistant":
            code = extract_code_from_message(m["content"])
            if not code:
                console.print("[red]No code to debug found.[/]")
                return None

            debug_prompt = (
                f"Fix this Python code based on the following error:\n\n"
                f"---\n{last_error_output}\n---\n\n"
                f"Original code:\n```python\n{code}\n```"
            )

            console.print("[yellow]🧠 Attempting to fix code...[/yellow]")
            fixed_response = stream_chat(debug_prompt, memory, config)
            fixed_code = extract_code_from_message(fixed_response)

            console.print("\n[yellow]Attempting to run fixed code...[/yellow]")
            output = run_code_in_docker(fixed_code)
            console.print(Panel.fit(output, title="Fixed Execution Output", border_style="green"))
            return output

    console.print("[red]No assistant message found to debug.[/]")
    return None
