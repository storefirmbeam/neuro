# src/core/registry.py
from __future__ import annotations
from typing import Callable, Dict, Any, Optional, List

class ToolSpec:
    """
    In-memory descriptor for a tool.

    kind:
      - "function": runner expects kwargs (or a single dict) and returns JSON-serializable output.
      - "custom":  runner may accept a raw string payload; we still expose it to OpenAI as a function
                   so the model always provides JSON arguments. Your runtime may treat it specially.
    """
    def __init__(
        self,
        *,
        name: str,
        kind: str,  # "custom" | "function"
        description: str,
        runner: Callable[..., Any],
        parameters: Optional[dict] = None,  # JSON Schema for function args
    ):
        if kind not in {"custom", "function"}:
            raise ValueError(f"Unsupported tool kind: {kind}")
        self.name = name
        self.kind = kind
        self.description = description
        # Default empty-object schema so the LLM still sends {} if there are no args.
        self.parameters = parameters or {"type": "object", "properties": {}}
        self.runner = runner

    def to_openai_tool(self) -> dict:
        """
        Convert to the OpenAI 'tools' shape.
        We ALWAYS expose as a function so the model reliably emits JSON args.
        """
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


_registry: Dict[str, ToolSpec] = {}


def register_tool(spec: ToolSpec) -> None:
    """Register a tool by name; raises if the name already exists."""
    if spec.name in _registry:
        raise ValueError(f"Tool already registered: {spec.name}")
    _registry[spec.name] = spec


def get_tool(name: str) -> Optional[ToolSpec]:
    """Return a tool spec or None if not found (avoid KeyError in the runtime)."""
    return _registry.get(name)


def all_tools() -> Dict[str, ToolSpec]:
    """Return a shallow copy of the registry."""
    return dict(_registry)


def as_openai_tools() -> List[dict]:
    """
    Produce the OpenAI tool list from the registry.
    - Exposes BOTH 'function' and 'custom' kinds as 'type': 'function'.
    - Uses each ToolSpec's JSON schema so the model sends correct kwargs.
    """
    return [spec.to_openai_tool() for spec in _registry.values()]
