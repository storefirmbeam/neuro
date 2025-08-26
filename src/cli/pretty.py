# src/cli/pretty.py
import os
from rich.console import Console
from .input_ui import multiline_input
from .commands import command_handler_factory

console = Console()

def _banner_fn(ctx: dict):
    os.system("cls" if os.name == "nt" else "clear")
    try:
        from src.cli.header import print_header
        print_header(ctx)  # expects {'model': ..., 'log_file': ...}
    except Exception:
        console.rule(f"[bold cyan]NEURO[/]  [dim]{ctx.get('model','')}[/dim]")

def run(client, log_file: str, default_model: str = "gpt-5-mini"):
    from src.core.runtime import run_repl

    # live context so :config and header reflect updates
    live_ctx = {"model": default_model, "log_file": log_file}

    # build base command handler with access to live_ctx
    base_handler = command_handler_factory(lambda: live_ctx)
    def handler(cmd: str):
        res = base_handler(cmd) or {}
        if res.get("set_model"):
            live_ctx["model"] = res["set_model"]  # keep in sync for :config
        return res

    def input_fn(prompt: str) -> str:
        return multiline_input(prompt).strip()

    run_repl(
        client=client,
        log_file=log_file,
        model=default_model,
        input_fn=input_fn,
        banner_fn=_banner_fn,     # runtime supplies current {'model', 'log_file'}
        command_handler=handler,  # <- use wrapped handler (do NOT overwrite it)
    )
