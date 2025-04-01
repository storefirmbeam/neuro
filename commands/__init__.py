# commands/__init__.py
from commands.run import handle_run
from commands.debug import handle_debug
from commands.refresh import handle_refresh
from commands.clear import handle_clear
from commands.setmodel import handle_setmodel
from commands.setlocal import handle_setlocal
from commands.config import handle_config
from commands.models import handle_models
from commands.help import handle_help


def handle_command(cmd, memory, config, console, last_error_output=None, models_dict=None):
    if cmd in [":exit", ":quit"]:
        console.print("[bold red]Goodbye!🚀[/]")
        exit(0)

    elif cmd == ":refresh":
        return handle_refresh(memory, console)

    elif cmd == ":clear":
        return handle_clear(console, config)

    elif cmd.startswith(":setmodel"):
        return handle_setmodel(cmd, config, console)

    elif cmd.startswith(":setlocal"):
        return handle_setlocal(cmd, config, console)

    elif cmd == ":config":
        return handle_config(config, console)

    elif cmd == ":models":
        return handle_models(console, models_dict)

    elif cmd == ":help":
        return handle_help(console)

    elif cmd == ":run":
        return handle_run(memory, console)

    elif cmd == ":debug":
        return handle_debug(memory, console, config, last_error_output)

    return False