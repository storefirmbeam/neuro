import argparse
import pyperclip
from ai_stream import stream_chat#, use_web_search
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
import os
from datetime import datetime
from header import print_header
import json
import shutil
from commands import handle_command
import readline  # Enables arrow key history navigation
from utils.input import multiline_input  # For multiline input in the terminal

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
    parser.add_argument("--config", help="Path to config file", default="~/.neuro_config.json")
    parser.add_argument("--list", help="List featured models", default="configs/models.json")
    args = parser.parse_args()

    # Expand user path
    config_path = os.path.expanduser(args.config)

    # If config doesn't exist, copy from default
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        shutil.copy("configs/default_config.json", config_path)

    # Load configuration
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

    last_error_output=""

    while True:
        try:
            #user_input = input("> ").strip()
            user_input = multiline_input("> ").strip()  # Use multiline input for better UX
            if not user_input:
                console.print("[bold red]⛔ Empty input, please try again.[/]")
                continue
            print("\n")
            if user_input.startswith(":"):
                result = handle_command(user_input, chat_memory, config, console, last_error_output, models_dict)
                
                if not user_input == ":clear":
                    print("\n")

                if result is not False:
                    last_error_output = result  # ✅ Capture output from :run or :debug
                    continue

            response = stream_chat(user_input, chat_memory, config)
            pyperclip.copy(response)
            log_conversation(user_input, response)
            print("\n")

        except KeyboardInterrupt:
            console.print("[bold red]⛔ Interrupted[/]\n")
            continue