# src/cli/pretty.py

import os
from contextlib import contextmanager
from typing import Callable, Iterator

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from .commands import command_handler_factory
from .input_ui import multiline_input


console = Console()


def _banner_fn(ctx: dict) -> None:
    os.system("cls" if os.name == "nt" else "clear")

    try:
        from src.cli.header import print_header

        print_header(ctx)
    except Exception:
        console.rule(
            f"[bold cyan]NEURO[/]  "
            f"[dim]{ctx.get('model', '')}[/dim]"
        )


@contextmanager
def live_markdown_stream() -> Iterator[Callable[[str], None]]:
    """Render accumulated Markdown while the response streams."""

    with Live(
        Markdown(""),
        console=console,
        refresh_per_second=15,
        transient=False,
        vertical_overflow="ellipsis",
    ) as live:

        def update(text: str) -> None:
            live.update(
                Markdown(text),
                refresh=True,
            )

        yield update


def run(
    client,
    log_file: str,
    default_model: str = "gpt-5.6-sol",
) -> None:
    from src.core.runtime import run_repl

    live_ctx = {
        "model": default_model,
        "log_file": log_file,
    }

    base_handler = command_handler_factory(
        lambda: live_ctx
    )

    def handler(cmd: str) -> dict:
        result = base_handler(cmd) or {}

        if result.get("set_model"):
            live_ctx["model"] = result["set_model"]

        return result

    def input_fn(prompt: str) -> str:
        return multiline_input(prompt).strip()

    run_repl(
        client=client,
        log_file=log_file,
        model=default_model,
        input_fn=input_fn,
        banner_fn=_banner_fn,
        command_handler=handler,
        stream_context_factory=live_markdown_stream,
    )