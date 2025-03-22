import argparse
import readline  # enables arrow key history
import pyperclip
from ai_stream import stream_chat#, use_web_search
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
import os
from datetime import datetime
from header import print_header
import json

console = Console()

# Log file
LOG_FILE = os.path.expanduser("~/.neuro.md")

# Message memory
#chat_memory = [{"role": "system", "content": "You are a helpful assistant."}]
chat_memory = []
def log_conversation(user_input, response):
    with open(LOG_FILE, "a") as f:
        f.write(f"\n### {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**You:** {user_input}\n\n")
        f.write(f"**AI:** {response}\n")

def load_config(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        console.print(f"[red]Error: File '{path}' not found.[/]")
        return {}
    except json.JSONDecodeError:
        console.print(f"[red]Error: File '{path}' is not a valid JSON file.[/]")
        return {}
    
def load_models(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        console.print(f"[red]Error: File '{path}' not found.[/]")
        return {}
    except json.JSONDecodeError:
        console.print(f"[red]Error: File '{path}' is not a valid JSON file.[/]")
        return {}

def main():
    parser = argparse.ArgumentParser(description="🤖 NEURO - Terminal LLM Client")
    parser.add_argument("prompt", nargs="*", help="Prompt to send to AI")
    parser.add_argument("--model", help="Override model in config.json")
    parser.add_argument("--local", action="store_true", help="Run in local mode (simulate)")
    parser.add_argument("--config", help="Path to config file", default="configs/config.json")
    parser.add_argument("--list", help="List featured models", default="configs/models.json")
    args = parser.parse_args()

    # Load configuration
    config_path = args.config
    config = load_config(config_path)

    # Load models from file
    models_file_path = args.list
    models_dict = load_models(models_file_path)

    # Override model/local if flags are used
    if args.model:
        config["model"] = args.model
    if args.local:
        config["local_mode"] = True

    if args.prompt:
        user_input = " ".join(args.prompt)
        print("\n")
        response = stream_chat(user_input, chat_memory, config)
        print("\n")
        pyperclip.copy(response)
        log_conversation(user_input, response)
        return

    os.system("clear")  # Linux/macOS
    print_header(config)

    while True:
        try:
            user_input = input("> ").strip()
            print("\n")
            if user_input.lower() in [":exit", ":quit"]:
                console.print("[bold red]Goodbye!🚀[/]")
                break
            elif user_input == ":refresh":
                chat_memory[:] = chat_memory[:1]
                console.print("[yellow]Memory cleared.[/]")
                continue
            elif user_input == ":clear":
                os.system("clear")      # Linux/macOS
                print_header(config)
                continue
            elif user_input.startswith(":setmodel "):
                new_model = user_input.split(":setmodel ")[1].strip()
                config["model"] = new_model
                console.print(f"[green]Model updated to:[/] {new_model}\n")
                continue
            elif user_input.startswith(":setlocal "):
                value = user_input.split(":setlocal ")[1].strip().lower()
                if value in ["true", "false"]:
                    config["local_mode"] = (value == "true")
                    console.print(f"[green]Local mode set to:[/] {config['local_mode']}")
                else:
                    console.print("[red]Invalid value. Use `true` or `false`.[/]")
                continue
            elif user_input == ":config":
                console.print_json(json.dumps(config, indent=2))
                print("\n")
                continue
            elif user_input == ":models":
                if not models_dict:
                    console.print("[red]No models available.[/]")
                else:
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

                print("\n")
                continue
            elif user_input == ":help":
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
                print("\n")
                continue

            response = stream_chat(user_input, chat_memory, config)
            pyperclip.copy(response)
            log_conversation(user_input, response)
            print("\n")
        except KeyboardInterrupt:
            console.print("[bold red]⛔ Interrupted[/]\n")
            continue
