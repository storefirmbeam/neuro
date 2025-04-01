# utils/code.py
import re

def extract_code_from_message(message: str) -> str:
    # Try to extract triple-backtick code block
    code_blocks = re.findall(r"```python\n(.*?)```", message, re.DOTALL)
    if code_blocks:
        return code_blocks[0].strip()
    
    # Fallback: Heuristic line stripping (no backticks)
    lines = message.splitlines()
    code_lines = []
    found_code = False

    for line in lines:
        if re.match(r'^\s*(import|def|class|if|for|while|try|print)', line):
            found_code = True
        if found_code:
            code_lines.append(line)
    
    return "\n".join(code_lines).strip()