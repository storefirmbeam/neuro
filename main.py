# main.py
from dotenv import load_dotenv
from openai import OpenAI
import os
import argparse

load_dotenv()

from src.tools import sandbox  # noqa: F401
from src.tools import homeassistant  # noqa: F401
from src.core.runtime import run_repl

LOG_FILE = os.path.expanduser("memory.md")
client = OpenAI()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", choices=["pretty"], help="Use the pretty CLI")
    parser.add_argument("--model", default="gpt-5-mini")
    args = parser.parse_args()

    if args.cli == "pretty":
        from src.cli.pretty import run as run_pretty
        run_pretty(client=client, log_file=LOG_FILE, default_model=args.model)
    else:
        run_repl(client=client, log_file=LOG_FILE, model=args.model)
