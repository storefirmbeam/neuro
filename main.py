# main.py
from dotenv import load_dotenv
from openai import OpenAI
import os

# Load env first (HA creds, SANDBOX_IMAGE, etc.)
load_dotenv()

# Import tools (side effect: they self-register)
from src.tools import sandbox  # noqa: F401
from src.tools import homeassistant  # noqa: F401

from src.core.runtime import run_repl

LOG_FILE = os.path.expanduser("memory.md")
client = OpenAI()

if __name__ == "__main__":
    run_repl(client=client, log_file=LOG_FILE, model="gpt-5-mini")
