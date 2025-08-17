# src/core/runtime.py
import sys
import json
import pathlib
from openai import OpenAI, BadRequestError
from .registry import as_openai_tools, get_tool


def _ensure_json_payload(s: str) -> str:
    try:
        json.loads(s)
        return s
    except Exception:
        return json.dumps({"stdout": s})


def _append_log(log_file: str, user: str, ai_text: str,
                tool_used: str = None, tool_input_len: int = 0, tool_output_preview: str = ""):
    pathlib.Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n### turn\n**You:** {user}\n\n**AI:** {ai_text}\n")
        if tool_used:
            f.write(
                f"\n_Tool used_: {tool_used}\n"
                f"_Input bytes_: {tool_input_len}\n"
                f"_Output_: {tool_output_preview}\n"
            )


def run_repl(*, client: OpenAI, log_file: str, model: str = "gpt-5-mini"):
    """
    REPL that supports multi-step tool chains in one user turn.
      - Stream assistant until a tool is requested (or completion).
      - If tool requested: run it, feed its output, and loop the stream again.
      - Continue until the model finishes without requesting another tool.
    """
    pathlib.Path(log_file).touch(exist_ok=True)
    last_response_id = None

    def _extract_tool_from_final(final):
        """
        Fallback: scan the completed response object for a function/custom tool call
        and return (tool_call_dict, raw_args_str). If none, (None, "").
        """
        try:
            out_items = getattr(final, "output", None) or []
            for item in out_items:
                itype = getattr(item, "type", None)
                if itype in ("function_call", "custom_tool_call"):
                    call_id = getattr(item, "call_id", None)
                    name = getattr(item, "name", None)
                    args = getattr(item, "arguments", None)
                    if args is None:
                        args = getattr(item, "input", None)
                    if isinstance(args, (dict, list)):
                        args = json.dumps(args, ensure_ascii=False)
                    return ({"call_id": call_id, "name": name, "kind": itype}, (args or "").strip())
        except Exception:
            pass
        return None, ""

    def stream_once(input_payload, prev_id: str | None):
        """
        Stream one pass given an input payload (user text OR function_call_output list item),
        return: (text_delta, next_prev_id, tool_call|None, raw_args_str, final_obj)
        """
        text_buf = []
        tool_call = None
        args_buf = []
        suppress_text = False

        with client.responses.stream(
            model=model,
            input=input_payload,
            tools=as_openai_tools(),
            parallel_tool_calls=False,
            previous_response_id=prev_id,
        ) as stream:
            for event in stream:
                et = event.type

                # Assistant text
                if et == "response.output_text.delta":
                    if not suppress_text:
                        delta = event.delta or ""
                        # Hide any narration like "to=functions.ha_service"
                        if "to=functions." in delta:
                            suppress_text = True
                            continue
                        sys.stdout.write(delta)
                        sys.stdout.flush()
                        text_buf.append(delta)

                # Tool item announced
                elif et in ("response.output_item.added", "response.output_item.done"):
                    item = getattr(event, "item", None)
                    if item and item.type in ("function_call", "custom_tool_call") and tool_call is None:
                        tool_call = {
                            "call_id": getattr(item, "call_id", None),
                            "name": getattr(item, "name", None),
                            "kind": item.type,
                        }
                        suppress_text = True
                        initial = getattr(item, "arguments", None)
                        if initial is None:
                            initial = getattr(item, "input", None)
                        if initial is not None:
                            if isinstance(initial, (dict, list)):
                                args_buf.append(json.dumps(initial, ensure_ascii=False))
                            else:
                                args_buf.append(str(initial))

                # Argument fragments (SDK-dependent)
                elif et in (
                    "response.function_call.arguments.delta",
                    "response.function_call.delta",
                    "response.tool_call.delta",
                ):
                    suppress_text = True
                    frag = getattr(event, "delta", None)
                    if frag:
                        args_buf.append(frag)

            final = stream.get_final_response()
            pre_text = "".join(text_buf)
            next_prev_id = final.id

        raw_args = "".join(args_buf).strip()

        # If tool detected but no args built, try final object
        if tool_call and not raw_args:
            _, final_args = _extract_tool_from_final(final)
            if final_args:
                raw_args = final_args

        # If no tool detected during stream, check final object anyway
        if not tool_call:
            final_call, final_args = _extract_tool_from_final(final)
            if final_call:
                tool_call = final_call
                raw_args = raw_args or final_args

        return pre_text, next_prev_id, tool_call, raw_args, final

    while True:
        try:
            user = input("\n> ")
        except KeyboardInterrupt:
            print("\n")
            break

        # Manual reset
        if user.strip().lower() in {"reset", "/reset", "/new"}:
            last_response_id = None
            print("🧹 Started a fresh thread.")
            continue

        # -------- Initial stream (from user message) --------
        try:
            full_text, prev_id, tool_call, raw_args, _ = stream_once(user, last_response_id)
        except BadRequestError as e:
            if "No tool output found for function call" in str(e):
                last_response_id = None
                print("\n[info] Resetting stalled thread and retrying once...\n")
                full_text, prev_id, tool_call, raw_args, _ = stream_once(user, None)
            else:
                raise

        # -------- Tool loop: run as many as the model asks for --------
        last_tool_name = None
        last_tool_raw_input_len = 0
        last_tool_output_preview = ""

        while tool_call:
            tool_name = tool_call.get("name") or "<unknown>"
            call_kind = tool_call.get("kind") or "function_call"
            last_tool_name = tool_name

            # DEBUG tip:
            # print(f"\n[debug] tool={tool_name} kind={call_kind} raw_args={raw_args!r}\n")

            # Execute the tool
            try:
                spec = get_tool(tool_name)
                if not spec:
                    raise RuntimeError(f"Tool not registered: {tool_name}")

                if call_kind == "function_call":
                    try:
                        args = json.loads(raw_args or "{}")
                    except Exception as e:
                        args = {}
                        tool_stdout = json.dumps(
                            {"error": f"args parse error: {e}", "tool": tool_name, "raw": (raw_args or '')[:200]}
                        )
                    else:
                        try:
                            try:
                                result = spec.runner(**(args or {}))
                            except TypeError:
                                result = spec.runner(args or {})
                        except Exception as e:
                            result = {"error": str(e), "tool": tool_name, "args_seen": args}

                        tool_stdout = (
                            json.dumps(result, ensure_ascii=False)
                            if isinstance(result, (dict, list))
                            else _ensure_json_payload(str(result))
                        )

                else:
                    # custom_tool_call
                    try:
                        result = spec.runner(raw_args)
                    except Exception as e:
                        result = {"error": str(e), "tool": tool_name}
                    tool_stdout = (
                        json.dumps(result, ensure_ascii=False)
                        if isinstance(result, (dict, list))
                        else _ensure_json_payload(str(result))
                    )

            except Exception as e:
                tool_stdout = json.dumps({"error": str(e), "tool": tool_name})

            last_tool_raw_input_len = len(raw_args or "")
            last_tool_output_preview = (tool_stdout or "")[:500]

            # Feed the tool output and continue streaming — the model may request another tool
            try:
                input_payload = [{
                    "type": "function_call_output",
                    "call_id": tool_call.get("call_id"),
                    "output": tool_stdout,
                }]
                post_text, prev_id, tool_call, raw_args, _ = stream_once(input_payload, prev_id)
                full_text += post_text  # accumulate visible text
            except BadRequestError as e:
                if "No tool output found for function call" in str(e):
                    # Clear the thread to avoid being stuck
                    last_response_id = None
                    print("\n[info] Resetting stalled thread and retrying once...\n")
                    post_text, prev_id, tool_call, raw_args, _ = stream_once(input_payload, None)
                    full_text += post_text
                else:
                    raise

        # -------- Finished the turn (no more tools requested) --------
        last_response_id = prev_id
        _append_log(
            log_file,
            user,
            full_text,
            tool_used=last_tool_name,
            tool_input_len=last_tool_raw_input_len,
            tool_output_preview=last_tool_output_preview,
        )
