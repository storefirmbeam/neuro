
HEADER = r"""
 ███╗   ██╗███████╗██╗   ██╗██████╗  ██████╗ 
 ████╗  ██║██╔════╝██║   ██║██╔══██╗██╔═══██╗
 ██╔██╗ ██║█████╗  ██║   ██║██████╔╝██║   ██║
 ██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██║   ██║
 ██║ ╚████║███████╗╚██████╔╝██║  ██║╚██████╔╝
 ╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ 

"""

def print_header(config):
    print("\033[96m" + HEADER + "\033[0m", flush=True)
    print(f"🚀 {config['model']} is running! Type a message and press Enter. Type ':exit' to quit.\n", flush=True)
