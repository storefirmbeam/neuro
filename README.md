# 🧠 neuro — Terminal AI Assistant

**neuro** is a flexible, fast, and developer-friendly terminal-based AI assistant.  
It supports both **OpenAI's, Anthropic's, and xAI's cloud models** and **local LLMs via Ollama**, giving you total control over your AI experience — online or offline.

---

## 🚀 Features

- 🌐 **Cloud + Local**: Seamlessly switch between OpenAI, Anthropic, xAI, and Ollama.
- 💬 **Streaming Responses**: Smooth, live Markdown rendering of output.
- 📍 **Location-Aware**: Built-in web tool uses your location to improve relevance.
- 🔧 **Configurable**: Change models, temperature, and mode via `config.json` or live commands.
- 📜 **Conversation Logging**: Automatically saves chats to Markdown logs.
- 🧠 **Memory Mode**: Keeps track of conversation history per session.
- 🎛️ **Command System**: Interactive commands like `:help`, `:setmodel`, `:models`, `:setlocal`, and more.

---

## 📦 Installation

```bash
git clone https://github.com/yourname/neuro
cd neuro
python -m venv Ai
source Ai/bin/activate
pip install -r requirements.txt
```

> ⚠️ You must have [Ollama](https://ollama.com) installed for local model support.

---

## 🧰 Configuration

Edit the `config.json` in the 'configs' directory:

```json
{
  "model": "gpt-4o",
  "user_location": {
    "country": "US",
    "city": "your-city",
    "region": "your-region",
    "timezone": "your-timezone"
  },
  "local_mode": false,
  "search_context_size": "medium"
}
```

---

## 💡 Usage

### One-off Prompt
```bash
python main.py "Explain quantum physics like I'm 10"
```

### Interactive Chat Mode
```bash
python main.py
```

---

## 🕹️ Interactive Commands

| Command                 | Description                                |
|-------------------------|--------------------------------------------|
| `:help`                 | Show help menu                             |
| `:clear`                | Clear the terminal screen and header       |
| `:refresh`              | Clear conversation memory                  |
| `:setmodel [name]`      | Change model in the current session        |
| `:setlocal true|false`  | Toggle between OpenAI and local mode       |
| `:config`               | View current loaded config                 |
| `:models`               | List available local models (Ollama)       |
| `exit` or `quit`        | Exit the assistant                         |

---

## 🧠 Example Models

### ☁️ OpenAI
- `gpt-4.5-preview`
- `gpt-4o`
- `gpt-4o-mini`
- `gpt-4`
- `o3-mini`
- `o1-pro`
- `o1-mini`
- `o1`

### 🔮 Anthropic
- `claude-3.7-sonnet-latest`
- `claude-3.5-haiku-latest`

### 🚀 Grok (xAI)
- `grok-2-latest`

### 🖥️ Local (Ollama)
- Any model you have installed via `ollama`, like:
  - `llama3:8b`
  - `mistral`
  - `codellama`
  - `phi3`

> ✅ To use local models:
> 1. Set `"local_mode": true` in `config.json`  
> 2. Set `"model"` to the name of your Ollama model  
> 3. List local models interactively with `:models`


---

## 🛠️ Dev Notes

- Built using `rich`, `openai`, `ollama`, `dotenv`, and `argparse`.
- Compatible with macOS, Linux, and Windows (with minor terminal tweaks).
- Terminal logs are stored in `~/.myai_history.md`.

---

## 🧪 Roadmap Ideas

- ✅ CLI flag for `--model` and `--local`
- 🔲 `:saveconfig` to persist runtime changes
- 🔲 Session export as `.txt` or `.json`
- 🔲 Voice-to-text input with `:voice`
- 🔲 Shell command execution in context

---

## 🙏 Credits

- Terminal UI: [Textual](https://www.textualize.io/) inspiration via `rich`
- Local LLM backend: [Ollama](https://ollama.com)
- Cloud models via [OpenAI](https://openai.com)

---

## 📜 License

MIT License

> Neuro is your fast, flexible, offline-ready terminal brain.
