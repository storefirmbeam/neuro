# commands/setmodel.py
def handle_setmodel(cmd, config, console):
    new_model = cmd.split(":setmodel", 1)[1].strip()
    if new_model:
        config["model"] = new_model
        console.print(f"[green]Model updated to:[/] {new_model}\n")
    else:
        console.print("[red]No model specified.[/]")
    return True