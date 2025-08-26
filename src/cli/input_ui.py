# src/cli/input_ui.py
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.markup import MarkdownLexer
import os
from pathlib import Path

bindings = KeyBindings()

@bindings.add("enter")
def _(event):
    event.current_buffer.validate_and_handle()

@bindings.add("escape", "enter")
def _(event):
    event.current_buffer.insert_text("\n")

style = Style.from_dict({
    "prompt": "ansicyan bold",
    "": "#ffffff",
})

# Make sure parent dir exists; touch the file so FileHistory can open it.
_hist_path = os.path.expanduser("~/.neuro_history")
Path(_hist_path).parent.mkdir(parents=True, exist_ok=True)
Path(_hist_path).touch(exist_ok=True)
_history = FileHistory(_hist_path)

def multiline_input(prompt_text="> "):
    session = PromptSession(
        lexer=PygmentsLexer(MarkdownLexer),
        key_bindings=bindings,
        style=style,
        history=_history,
        multiline=True,
        prompt_continuation="... ".rjust(len(prompt_text)),
    )
    return session.prompt([("class:prompt", prompt_text)])