#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import platform
import shlex
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown

from src.cli.pretty import live_markdown_stream

# Importing these modules registers their tools with Neuro.
from src.tools import homeassistant  # noqa: F401
from src.tools import sandbox  # noqa: F401
from src.core.runtime import run_once, run_repl

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"

NEURO_HOME = Path(
    os.getenv(
        "NEURO_HOME",
        Path.home() / ".neuro",
    )
).expanduser()

LOG_FILE = Path(
    os.getenv(
        "NEURO_HISTORY_FILE",
        NEURO_HOME / "history.md",
    )
).expanduser()

DEFAULT_MODEL = os.getenv(
    "NEURO_MODEL",
    "gpt-5.6-sol",
)


NORMAL_INSTRUCTIONS = """
You are Neuro, a terminal-native AI assistant.

Answer the user's request directly and accurately. You may use any available
tools when they would improve the answer. The user may be invoking you from an
interactive terminal, an inline shell command, a pipe, or a script.
""".strip()


COMMAND_INSTRUCTIONS = """
You are Neuro operating in shell-command mode.

Return only the shell command needed to complete the user's request.

Requirements:
- Do not use Markdown.
- Do not use code fences.
- Do not use backticks.
- Do not include an explanation.
- Do not include a label such as "Command:".
- Do not include introductory or closing text.
- Return one directly runnable command whenever possible.
- Use available tools when needed to determine the correct command.
- Never claim that a command was executed unless a tool actually executed it.
""".strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neuro",
        description="Neuro terminal AI assistant",
    )

    parser.add_argument(
        "prompt",
        nargs="*",
        help="Inline prompt. Leave empty to start interactive mode.",
    )

    parser.add_argument(
        "-c",
        "--command",
        action="store_true",
        help="Return only a shell command.",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress streaming and print only the final response.",
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model to use. Default: {DEFAULT_MODEL}",
    )

    parser.add_argument(
        "--cli",
        choices=("pretty", "plain"),
        default="pretty",
        help="Interactive interface to use when no prompt is provided.",
    )

    return parser


def read_stdin() -> str:
    """Read piped input without blocking normal interactive terminal use."""

    if sys.stdin.isatty():
        return ""

    return sys.stdin.read().strip()


def combine_prompt(
    argument_prompt: str,
    stdin_text: str,
) -> str:
    """Combine a command-line request with optional piped content."""

    if argument_prompt and stdin_text:
        return (
            f"{argument_prompt}\n\n"
            "The following content was provided through standard input:\n\n"
            f"{stdin_text}"
        )

    if argument_prompt:
        return argument_prompt

    return stdin_text


def command_context() -> str:
    """
    Give command mode enough local context to choose an appropriate command.

    This does not execute anything.
    """

    shell_path = os.getenv("SHELL", "")
    shell_name = Path(shell_path).name if shell_path else "unknown"
    current_directory = Path.cwd()

    return (
        f"Operating system: {platform.system()}\n"
        f"Shell: {shell_name}\n"
        f"Current directory: {current_directory}"
    )


def run_inline(
    *,
    client: OpenAI,
    prompt: str,
    model: str,
    command_mode: bool,
    quiet: bool,
) -> int:
    """Run one inline Neuro request."""

    if command_mode:
        prompt = f"Only output the shell command:\n\n{prompt}"

    # Command and quiet modes must remain plain for shell usage,
    # pipes, command substitution, and scripts.
    if command_mode or quiet:
        result = run_once(
            client=client,
            prompt=prompt,
            log_file=str(LOG_FILE),
            model=model,
            emit_output=False,
        )

        print(result.text.strip())
        return 0

    # Normal inline mode streams through Rich Live Markdown.
    with live_markdown_stream() as stream_callback:
        run_once(
            client=client,
            prompt=prompt,
            log_file=str(LOG_FILE),
            model=model,
            emit_output=False,
            stream_callback=stream_callback,
        )

    return 0


def run_interactive(
    *,
    client: OpenAI,
    model: str,
    cli_mode: str,
) -> int:
    """Start Neuro's existing interactive interface."""

    if cli_mode == "pretty":
        from src.cli.pretty import run as run_pretty

        run_pretty(
            client=client,
            log_file=str(LOG_FILE),
            default_model=model,
        )
    else:
        run_repl(
            client=client,
            log_file=str(LOG_FILE),
            model=model,
        )

    return 0


def main() -> int:
    load_dotenv(
        dotenv_path=ENV_FILE,
        override=True,
    )

    parser = build_parser()
    args = parser.parse_args()

    LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    argument_prompt = " ".join(args.prompt).strip()
    stdin_text = read_stdin()
    prompt = combine_prompt(argument_prompt, stdin_text)

    client = OpenAI()

    if prompt:
        return run_inline(
            client=client,
            prompt=prompt,
            model=args.model,
            command_mode=args.command,
            quiet=args.quiet,
        )

    return run_interactive(
        client=client,
        model=args.model,
        cli_mode=args.cli,
    )


if __name__ == "__main__":
    raise SystemExit(main())