# commands/clear.py
import os
from header import print_header

def handle_clear(console, config):
    os.system("clear")
    print_header(config)
    return True