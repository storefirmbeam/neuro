# commands/setlocal.py
def handle_setlocal(cmd, config, console):
    value = cmd.split(":setlocal", 1)[1].strip().lower()
    if value in ["true", "false"]:
        config["local_mode"] = (value == "true")
        console.print(f"[green]Local mode set to:[/] {config['local_mode']}")
    else:
        console.print("[red]Invalid value. Use `true` or `false`.")
    return True
