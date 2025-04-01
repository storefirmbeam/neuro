# commands/config.py
import json

def handle_config(config, console):
    console.print_json(json.dumps(config, indent=2))
    return True