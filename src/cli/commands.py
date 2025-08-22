# src/cli/commands.py
from rich.console import Console
from rich.table import Table

console = Console()

HELP_TEXT = """[bold cyan]:commands[/]

  :help                  Show this help
  :clear                 Clear screen and redraw header
  :refresh               Reset the thread (forget previous turns)
  :setmodel <name>       Switch model (e.g., gpt-5-mini)
  :models                Show a few example models
  :config                Show current runtime bits
  :quit / :exit          Quit
"""

EXAMPLE_MODELS = [
    "gpt-5-mini",
    "gpt-5",
    "gpt-4.1-mini",
    "o3-mini",
]

def _models_table():
    t = Table(title="Featured Models")
    t.add_column("Model", style="green", no_wrap=True)
    t.add_column("Notes", style="white")
    for m in EXAMPLE_MODELS:
        t.add_row(m, "Available via OpenAI Responses API")
    return t

def command_handler_factory(context_getter):
    """
    context_getter() must return a dict with keys: model (str), log_file (str)
    We return a function(cmd:str)->dict (action map for runtime).
    """
    def handle(cmd: str):
        c = cmd.strip()

        if c in (":quit", ":exit"):
            return {"handled": True, "quit": True}

        if c == ":help":
            console.print(HELP_TEXT)
            return {"handled": True}

        if c == ":clear":
            return {"handled": True, "clear_screen": True}

        if c == ":refresh":
            return {"handled": True, "reset_thread": True}

        if c.startswith(":setmodel"):
            parts = c.split()
            if len(parts) < 2:
                console.print("[yellow]Usage:[/] :setmodel <model_name>")
                return {"handled": True}
            new_model = parts[1]
            return {"handled": True, "set_model": new_model}

        if c == ":models":
            console.print(_models_table())
            return {"handled": True}

        if c == ":config":
            ctx = context_getter() or {}
            console.print(f"[cyan]Model:[/] {ctx.get('model')}")
            console.print(f"[cyan]Log file:[/] {ctx.get('log_file')}")
            return {"handled": True}

        return {"handled": False}
    return handle
