#utils/input.py
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.python import PythonLexer

bindings = KeyBindings()

# Enter submits immediately
@bindings.add('enter')
def submit(event):
    event.current_buffer.validate_and_handle()

# Alt+Enter (escape followed by enter) inserts newline
@bindings.add('escape', 'enter')
def alt_enter_newline(event):
    event.current_buffer.insert_text('\n')

style = Style.from_dict({
    'prompt': 'ansicyan bold',
    '': '#ffffff',
})

def multiline_input(prompt_text="> "):
    session = PromptSession(
        lexer=PygmentsLexer(PythonLexer),
        key_bindings=bindings,
        style=style,
        multiline=True,
        prompt_continuation='... '.rjust(len(prompt_text))
    )
    user_input = session.prompt([('class:prompt', prompt_text)])
    return user_input.strip()
