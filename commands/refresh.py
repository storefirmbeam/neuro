# commands/refresh.py
def handle_refresh(memory, console):
    memory[:] = memory[:1]
    console.print("[yellow]Memory cleared.[/]")
    return True
