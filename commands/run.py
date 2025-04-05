# commands/run.py
# from rich.panel import Panel
# from utils.sandbox import run_steps_in_docker
# from utils.parsers import parse_ai_response

# def handle_run(memory, console):
#     for m in reversed(memory):
#         if m["role"] == "assistant":
#             steps = parse_ai_response(m["content"])
#             if not steps:
#                 console.print("[red]No runnable steps found in assistant message.[/]")
#                 return None

#             console.print("[purple]🚀 Executing parsed steps...[/purple]\n")
#             output = run_steps_in_docker(steps)
#             console.print(Panel.fit(output, title="Execution Output", border_style="green"))
#             return output

#     console.print("[red]No assistant message found to execute.[/]")
#     return None

# commands/run.py
from rich.panel import Panel
from rich.console import Console
from utils.parser_new import parse_ai_response  # updated parser
from utils.sandbox_new import run_steps_in_docker  # updated executor

def handle_run(memory, console: Console, verbose=False):
    for m in reversed(memory):
        if m["role"] == "assistant":
            console.print("[bold blue]🧠 Parsing AI response...[/bold blue]\n")
            steps = parse_ai_response(m["content"])
            if not steps:
                console.print("[red]❌ No actionable steps found in the assistant message.[/red]")
                return None

            console.print("\n[purple]🚀 Executing parsed steps...[/purple]\n")
            output = run_steps_in_docker(steps, verbose=verbose)
            console.print(Panel.fit(output, title="Execution Output", border_style="green"))
            return output

    console.print("[red]No assistant message found to execute.[/red]")
    return None
