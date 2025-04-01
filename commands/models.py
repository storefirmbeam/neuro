# commands/models.py
from rich.panel import Panel

def handle_models(console, models_dict):
    if not models_dict:
        console.print("[red]No models available.[/]")
        return True

    model_panel_content = "\n".join(
        f"[bold]{provider}[/]\n    " + "\n    ".join(f"[cyan]{model}[/cyan]" for model in models)
        for provider, models in models_dict.items()
    )

    full_content = (
        "[bold cyan]🤖 NEURO - Terminal LLM Client[/bold cyan]\n\n"
        "[bold]Supported Models:[/bold]\n\n"
        + model_panel_content
    )

    console.print(Panel.fit(
        full_content,
        title=":models",
        border_style="cyan"
    ))
    return True