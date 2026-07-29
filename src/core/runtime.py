# src/core/runtime.py

from __future__ import annotations

import json
import os
import pathlib
import sys
from dataclasses import dataclass
from typing import Any, Callable, Optional

from openai import BadRequestError, OpenAI
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from contextlib import nullcontext

from .registry import get_tool, runtime_tools


console = Console(stderr=True)


@dataclass
class TurnResult:
    """Result returned after one complete Neuro turn."""

    text: str
    response_id: str | None
    tool_used: str | None = None
    tool_input_len: int = 0
    tool_output_preview: str = ""


def _ensure_json_payload(value: str) -> str:
    """Ensure tool output sent to OpenAI is valid JSON."""

    try:
        json.loads(value)
        return value
    except Exception:
        return json.dumps({"stdout": value})


def _append_log(
    log_file: str,
    user: str,
    ai_text: str,
    tool_used: str | None = None,
    tool_input_len: int = 0,
    tool_output_preview: str = "",
) -> None:
    """Append a completed Neuro turn to the global history file."""

    path = pathlib.Path(log_file).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as file:
        file.write(
            "\n### turn\n"
            f"**You:** {user}\n\n"
            f"**AI:** {ai_text}\n"
        )

        if tool_used:
            file.write(
                f"\n_Tool used_: {tool_used}\n"
                f"_Input bytes_: {tool_input_len}\n"
                f"_Output_: {tool_output_preview}\n"
            )


def _extract_tool_from_final(
    final: Any,
) -> tuple[dict[str, Any] | None, str]:
    """
    Scan a completed response for a local function/custom tool call.

    Returns:
        A tuple containing the tool-call information and raw arguments.
    """

    try:
        output_items = getattr(final, "output", None) or []

        for item in output_items:
            item_type = getattr(item, "type", None)

            if item_type not in ("function_call", "custom_tool_call"):
                continue

            call_id = getattr(item, "call_id", None)
            name = getattr(item, "name", None)
            arguments = getattr(item, "arguments", None)

            if arguments is None:
                arguments = getattr(item, "input", None)

            if isinstance(arguments, (dict, list)):
                arguments = json.dumps(arguments, ensure_ascii=False)

            tool_call = {
                "call_id": call_id,
                "name": name,
                "kind": item_type,
            }

            return tool_call, str(arguments or "").strip()

    except Exception:
        pass

    return None, ""


def _run_registered_tool(
    tool_call: dict[str, Any],
    raw_args: str,
) -> str:
    """Execute a registered local Neuro tool."""

    tool_name = tool_call.get("name") or "<unknown>"
    call_kind = tool_call.get("kind") or "function_call"

    spec = get_tool(tool_name)

    if not spec:
        return json.dumps(
            {
                "error": f"Tool not registered: {tool_name}",
                "tool": tool_name,
            }
        )

    if call_kind == "function_call":
        try:
            args = json.loads(raw_args or "{}")
        except Exception as error:
            return json.dumps(
                {
                    "error": f"Arguments could not be parsed: {error}",
                    "tool": tool_name,
                    "raw": (raw_args or "")[:500],
                }
            )

        try:
            try:
                result = spec.runner(**(args or {}))
            except TypeError:
                result = spec.runner(args or {})
        except Exception as error:
            result = {
                "error": str(error),
                "tool": tool_name,
                "args_seen": args,
            }

    else:
        # custom_tool_call
        try:
            result = spec.runner(raw_args)
        except Exception as error:
            result = {
                "error": str(error),
                "tool": tool_name,
            }

    if isinstance(result, (dict, list)):
        return json.dumps(result, ensure_ascii=False)

    return _ensure_json_payload(str(result))


def _stream_response(
    *,
    client: OpenAI,
    model: str,
    input_payload: Any,
    previous_response_id: str | None,
    instructions: str | None,
    emit_output: bool,
    stream_callback: Callable[[str], None] | None = None,
) -> tuple[str, str | None, dict[str, Any] | None, str, Any]:
    """
    Stream one Responses API request.

    The input may be normal user text or a function_call_output payload.
    """

    text_buffer: list[str] = []
    argument_buffer: list[str] = []
    tool_call: dict[str, Any] | None = None
    suppress_text = False

    request_options: dict[str, Any] = {
        "model": model,
        "input": input_payload,
        "tools": runtime_tools(),
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "previous_response_id": previous_response_id,
    }

    stdout_context = (
        nullcontext()
        if stream_callback is not None
        else patch_stdout(raw=True)
    )

    with stdout_context:
        with client.responses.stream(**request_options) as stream:
            for event in stream:
                event_type = event.type

                if event_type == "response.output_text.delta":
                    if suppress_text:
                        continue

                    delta = event.delta or ""

                    # Prevent accidental internal tool narration from appearing.
                    if "to=functions." in delta:
                        suppress_text = True
                        continue

                    text_buffer.append(delta)

                    if stream_callback:
                        stream_callback("".join(text_buffer))
                    elif emit_output:
                        sys.stdout.write(delta)
                        sys.stdout.flush()

                elif event_type in (
                    "response.output_item.added",
                    "response.output_item.done",
                ):
                    item = getattr(event, "item", None)

                    if (
                        item
                        and item.type in ("function_call", "custom_tool_call")
                        and tool_call is None
                    ):
                        tool_call = {
                            "call_id": getattr(item, "call_id", None),
                            "name": getattr(item, "name", None),
                            "kind": item.type,
                        }

                        suppress_text = True

                        initial_arguments = getattr(item, "arguments", None)

                        if initial_arguments is None:
                            initial_arguments = getattr(item, "input", None)

                        if initial_arguments is not None:
                            if isinstance(initial_arguments, (dict, list)):
                                argument_buffer.append(
                                    json.dumps(
                                        initial_arguments,
                                        ensure_ascii=False,
                                    )
                                )
                            else:
                                argument_buffer.append(
                                    str(initial_arguments)
                                )

                elif event_type in (
                    "response.function_call.arguments.delta",
                    "response.function_call.delta",
                    "response.tool_call.delta",
                ):
                    suppress_text = True
                    fragment = getattr(event, "delta", None)

                    if fragment:
                        argument_buffer.append(fragment)

            final = stream.get_final_response()

    response_text = "".join(text_buffer)
    response_id = getattr(final, "id", None)

    if emit_output and response_text and not response_text.endswith("\n"):
        sys.stdout.write("\n")
        sys.stdout.flush()

    raw_args = "".join(argument_buffer).strip()

    if tool_call and not raw_args:
        _, final_args = _extract_tool_from_final(final)

        if final_args:
            raw_args = final_args

    if not tool_call:
        final_tool_call, final_args = _extract_tool_from_final(final)

        if final_tool_call:
            tool_call = final_tool_call
            raw_args = raw_args or final_args

    return response_text, response_id, tool_call, raw_args, final


def run_turn(
    *,
    client: OpenAI,
    user: str,
    model: str = "gpt-5.6-sol",
    log_file: str,
    previous_response_id: str | None = None,
    instructions: str | None = None,
    emit_output: bool = True,
    stream_callback: Callable[[str], None] | None = None,
) -> TurnResult:
    """
    Run one complete Neuro turn.

    This function is shared by both inline and interactive modes. It handles:

    - OpenAI streaming
    - Hosted tools such as web search
    - Registered local Neuro tools
    - Multi-step tool chains
    - Response-ID continuation
    - History logging
    """

    pathlib.Path(log_file).expanduser().parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        (
            full_text,
            response_id,
            tool_call,
            raw_args,
            _,
        ) = _stream_response(
            client=client,
            model=model,
            input_payload=user,
            previous_response_id=previous_response_id,
            instructions=instructions,
            emit_output=emit_output,
            stream_callback=stream_callback,
        )

    except BadRequestError as error:
        if (
            previous_response_id
            and "No tool output found for function call" in str(error)
        ):
            console.print(
                "[yellow]Previous conversation state was unavailable. "
                "Retrying as a fresh turn.[/yellow]"
            )

            (
                full_text,
                response_id,
                tool_call,
                raw_args,
                _,
            ) = _stream_response(
                client=client,
                model=model,
                input_payload=user,
                previous_response_id=None,
                instructions=instructions,
                emit_output=emit_output,
                stream_callback=stream_callback,
            )
        else:
            raise

    last_tool_name: str | None = None
    last_tool_input_len = 0
    last_tool_output_preview = ""

    streamed_text = full_text

    while tool_call:
        tool_name = tool_call.get("name") or "<unknown>"
        last_tool_name = tool_name

        tool_output = _run_registered_tool(
            tool_call=tool_call,
            raw_args=raw_args,
        )

        last_tool_input_len = len(raw_args or "")
        last_tool_output_preview = tool_output[:500]

        tool_output_payload = [
            {
                "type": "function_call_output",
                "call_id": tool_call.get("call_id"),
                "output": tool_output,
            }
        ]

        def chained_stream_callback(text: str) -> None:
            if stream_callback:
                stream_callback(streamed_text + text)

        (
            post_text,
            response_id,
            tool_call,
            raw_args,
            _,
        ) = _stream_response(
            client=client,
            model=model,
            input_payload=tool_output_payload,
            previous_response_id=response_id,
            instructions=instructions,
            emit_output=emit_output,
            stream_callback=chained_stream_callback,
        )

        full_text += post_text
        streamed_text = full_text

    _append_log(
        log_file=log_file,
        user=user,
        ai_text=full_text,
        tool_used=last_tool_name,
        tool_input_len=last_tool_input_len,
        tool_output_preview=last_tool_output_preview,
    )

    return TurnResult(
        text=full_text,
        response_id=response_id,
        tool_used=last_tool_name,
        tool_input_len=last_tool_input_len,
        tool_output_preview=last_tool_output_preview,
    )


def run_once(
    *,
    client: OpenAI,
    prompt: str,
    log_file: str,
    model: str = "gpt-5.6-sol",
    instructions: str | None = None,
    emit_output: bool = True,
    stream_callback: Callable[[str], None] | None = None,
) -> TurnResult:
    """
    Run one inline Neuro request.

    Inline requests are fresh by default, but they are still logged and have
    full access to all Neuro tools.
    """

    return run_turn(
        client=client,
        user=prompt,
        model=model,
        log_file=log_file,
        previous_response_id=None,
        instructions=instructions,
        emit_output=emit_output,
        stream_callback=stream_callback,
    )

def run_repl(
    *,
    client: OpenAI,
    log_file: str,
    model: str = "gpt-5.6-sol",
    input_fn: Optional[Callable[[str], str]] = None,
    banner_fn: Optional[Callable[[dict], None]] = None,
    command_handler: Optional[Callable[[str], dict]] = None,
    stream_context_factory: Optional[Callable[[], Any]] = None,
) -> None:
    """Run Neuro's interactive conversation interface."""

    log_path = pathlib.Path(log_file).expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)

    last_response_id: str | None = None
    current_model = model

    if banner_fn:
        try:
            banner_fn(
                {
                    "model": current_model,
                    "log_file": str(log_path),
                }
            )
        except Exception:
            pass

    while True:
        try:
            user = (input_fn or input)("> ").strip()

            if not user:
                continue

            if user.startswith(":") and command_handler:
                try:
                    action = command_handler(user) or {}
                except Exception as error:
                    console.print(
                        f"[bold red]Command error:[/] {error}"
                    )
                    continue

                if action.get("handled"):
                    if action.get("quit"):
                        print("Goodbye! 🚀")
                        break

                    if action.get("clear_screen"):
                        os.system(
                            "cls" if os.name == "nt" else "clear"
                        )

                        if banner_fn:
                            try:
                                banner_fn(
                                    {
                                        "model": current_model,
                                        "log_file": str(log_path),
                                    }
                                )
                            except Exception:
                                pass

                    if action.get("reset_thread"):
                        last_response_id = None
                        print("[info] Thread context cleared.\n")

                    if action.get("set_model"):
                        current_model = action["set_model"]
                        print(
                            f"[info] Model set -> {current_model}\n"
                        )

                    continue

            if user.lower() in {"reset", "/reset", "/new"}:
                last_response_id = None
                print("🧹 Started a fresh thread.")
                continue

            if stream_context_factory:
                with stream_context_factory() as stream_callback:
                    result = run_turn(
                        client=client,
                        user=user,
                        model=current_model,
                        log_file=str(log_path),
                        previous_response_id=last_response_id,
                        emit_output=False,
                        stream_callback=stream_callback,
                    )
            else:
                result = run_turn(
                    client=client,
                    user=user,
                    model=current_model,
                    log_file=str(log_path),
                    previous_response_id=last_response_id,
                    emit_output=True,
                    stream_callback=None,
                )

            last_response_id = result.response_id

        except KeyboardInterrupt:
            print("\n[ctrl-c] (use :quit to exit)\n")

        except EOFError:
            print("\nGoodbye! 🚀")
            break

        except Exception as error:
            console.print(f"[bold red]\nERROR:[/] {error}\n")