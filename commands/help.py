# commands/help.py
from rich.panel import Panel

def handle_help(console):
    console.print(Panel.fit(
        "[bold cyan]🤖 NEURO - Terminal LLM Client[/bold cyan]\n\n"
        "[bold]Commands:[/bold]\n"
        "[yellow]:help[/yellow]                   Show this help message\n"
        "[yellow]:config[/yellow]                 Show current config\n"
        "[yellow]:setmodel[/yellow] <model>       Set the model in config\n"
        "[yellow]:setlocal[/yellow] <true/false>  Toggle local mode on/off\n"
        "[yellow]:refresh[/yellow]                Clear chat memory (except system prompt)\n"
        "[yellow]:clear[/yellow]                  Clear terminal and show header again\n"
        "[yellow]exit[/yellow] or [yellow]quit[/yellow]  Exit the program\n",
        title=":help",
        border_style="cyan"
    ))
    return True
