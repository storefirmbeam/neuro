from openai import OpenAI
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from time import sleep
from dotenv import load_dotenv
from ollama import chat # type: ignore
import anthropic
import os

load_dotenv()

console = Console()

def stream_chat(user_input: str, memory: list, config: dict) -> str:
    memory.append({"role": "user", "content": user_input})

    # Check if local mode is enabled
    if config.get("local_mode", True):
        client = OpenAI(
            base_url = 'http://localhost:11434/v1',
            api_key='ollama', # required, but unused
        )

        stream = client.chat.completions.create(
            model=config["model"],
            messages=memory,
            stream=True,
        )
        
        full_text = ""
        md_render = Markdown(full_text)

        with Live(md_render, console=console, refresh_per_second=10) as live:
            for chunk in stream:
                # This works because the OpenAI-compatible Ollama wrapper uses choices[0].delta.content
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    token = delta.content
                    full_text += token
                    md_render = Markdown(full_text)
                    live.update(md_render)
                    sleep(0.01)

        memory.append({"role": "assistant", "content": full_text})
        return full_text
    
    # Check if using Grok model
    elif "grok" in config["model"]:
        client = OpenAI(
            base_url="https://api.x.ai/v1",
            api_key=os.getenv('XAI_API_KEY'),
        )
        stream = client.chat.completions.create(
            model=config["model"],
            messages=memory,
            stream=True,
        )
        
        full_text = ""
        md_render = Markdown(full_text)

        with Live(md_render, console=console, refresh_per_second=10) as live:
            for chunk in stream:
                # This works because the OpenAI-compatible Ollama wrapper uses choices[0].delta.content
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    token = delta.content
                    full_text += token
                    md_render = Markdown(full_text)
                    live.update(md_render)
                    sleep(0.01)

        memory.append({"role": "assistant", "content": full_text})
        return full_text
    
    # Check if using Claude
    elif "claude" in config["model"]:
        client = anthropic.Anthropic()

        stream = client.messages.create(
            max_tokens=2048,
            messages=memory,
            model=config["model"],
            stream=True,
        ) 

        full_text = ""
        md_render = Markdown(full_text)

        # Use the rich Live context manager to update markdown display
        with Live(md_render, console=console, refresh_per_second=10) as live:
            for chunk in stream:
                # Check for content_block_delta type events
                if chunk.type == 'content_block_delta':
                    delta = chunk.delta

                    # Append text to the full_text only if there's valid text content
                    if delta and delta.text:
                        token = delta.text
                        full_text += token
                        md_render = Markdown(full_text)
                        live.update(md_render)
                        sleep(0.01) # use time.sleep to introduce a brief pause
        
        memory.append({"role": "assistant", "content": full_text})
        return full_text
    
    # Else try OpenAI
    else:
        client = OpenAI()
        stream = client.responses.create(
            model=config["model"],
            input=memory,
            stream=True,
            tools=[{
                "type": "web_search_preview_2025_03_11",
                "search_context_size": config.get("search_context_size", "medium"), # Default: "medium"
                "user_location": {
                    "type": "approximate",
                    **config["user_location"]
                }
            }]
        )

        full_text = ""
        md_render = Markdown(full_text)

        with Live(md_render, console=console, refresh_per_second=10) as live:
            for event in stream:
                if event.type == "response.output_text.delta":
                    token = event.delta
                    full_text += token
                    md_render = Markdown(full_text)
                    live.update(md_render)
                    sleep(0.01)

        memory.append({"role": "assistant", "content": full_text})
        return full_text