# src/tools/homeassistant.py
import os
import json
import requests
import threading
import time
import re
import difflib
from datetime import datetime
from ..core.registry import register_tool, ToolSpec

# ----------- HTTP client (REST) -----------
HA_BASE = (os.getenv("HA_BASE_URL", "http://localhost:8123") or "").rstrip("/")
HA_TOKEN = os.getenv("HA_TOKEN", "") or ""

_session = requests.Session()
# Always send JSON; add Authorization only if present.
_session.headers.update({"Content-Type": "application/json"})
if HA_TOKEN:
    _session.headers.update({"Authorization": f"Bearer {HA_TOKEN}"})


def _ha_ok():
    """Quick sanity check that HA is reachable and token (if present) works."""
    if not HA_TOKEN:
        raise RuntimeError("HA_TOKEN missing in env")
    r = _session.get(f"{HA_BASE}/api/", timeout=5)
    r.raise_for_status()


def _safe_json(r: requests.Response):
    try:
        return r.json()
    except Exception:
        try:
            txt = r.text
        except Exception:
            txt = ""
        return {"text": txt, "status": getattr(r, "status_code", None)}


def ha_service(
    domain: str,
    service: str,
    service_data: dict | None = None,
    target: dict | None = None,
    data: dict | None = None,           # alias for service_data
    entity_id: str | list | None = None # alias convenience
):
    """
    Call any HA service at /api/services/{domain}/{service}.
    Accepts aliases (data, entity_id) and optional target (entity_id/device_id/area_id).
    """
    _ha_ok()

    # Normalize payload: merge aliases into service_data
    body = dict(service_data or {})
    if isinstance(data, dict):
        body.update(data)

    # entity_id can be a string or list; if provided and not already set in body, add it
    if entity_id is not None and "entity_id" not in body:
        body["entity_id"] = entity_id

    # If target provided, HA accepts top-level target dict
    # BUT also accepts top-level entity_id/device_id/area_id.
    # If user supplied {"entity_id": "..."} inside target, prefer explicit "target".
    payload = dict(body)
    if isinstance(target, dict) and target:
        payload = {"target": target, **{k: v for k, v in body.items() if k != "entity_id"}}
        # If body already had entity_id and target also has entity_id, prefer target’s
        if "entity_id" in body and "entity_id" not in target:
            payload["target"] = dict(target, entity_id=body["entity_id"])

    r = _session.post(
        f"{HA_BASE}/api/services/{domain}/{service}",
        data=json.dumps(payload),
        timeout=12,
    )
    return {"status": r.status_code, "json": _safe_json(r)}


def ha_get_state(entity_id: str):
    """Get state & attributes of a single entity."""
    _ha_ok()
    r = _session.get(f"{HA_BASE}/api/states/{entity_id}", timeout=8)
    return {"status": r.status_code, "json": _safe_json(r)}


def ha_fire_event(event_type: str, event_data: dict | None = None):
    """Fire a custom event on HA's event bus."""
    _ha_ok()
    r = _session.post(
        f"{HA_BASE}/api/events/{event_type}",
        data=json.dumps(event_data or {}),
        timeout=8,
    )
    return {"status": r.status_code, "json": _safe_json(r)}


def ha_template(template: str):
    """Render a Jinja template on the HA server."""
    _ha_ok()
    r = _session.post(
        f"{HA_BASE}/api/template",
        data=json.dumps({"template": template}),
        timeout=8,
    )
    return {"status": r.status_code, "json": _safe_json(r)}


# ----------- Health & Discovery / Resolver -----------
def ha_health():
    """Quick connectivity + inventory snapshot."""
    _ha_ok()
    info_r = _session.get(f"{HA_BASE}/api/config", timeout=5)
    states_r = _session.get(f"{HA_BASE}/api/states", timeout=10)
    info = _safe_json(info_r)
    states = _safe_json(states_r)
    if isinstance(states, dict):
        # If it failed, return what we have
        return {"base": HA_BASE, "info": info, "states_error": states}

    by_domain = {}
    for s in states:
        ent = s.get("entity_id", "")
        dom = ent.split(".")[0] if "." in ent else "other"
        by_domain[dom] = by_domain.get(dom, 0) + 1
    return {
        "base": HA_BASE,
        "version": info.get("version"),
        "unit_system": info.get("unit_system"),
        "entities_total": len(states),
        "by_domain": dict(sorted(by_domain.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def _norm(s: str) -> str:
    s = (s or "").casefold()
    s = re.sub(r"[\W_]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _slug(s: str) -> str:
    return re.sub(r"\s+", "_", _norm(s))


def ha_list_states(domain: str | None = None):
    _ha_ok()
    r = _session.get(f"{HA_BASE}/api/states", timeout=10)
    r.raise_for_status()
    data = r.json()
    if domain:
        data = [s for s in data if s.get("entity_id", "").startswith(domain + ".")]
    return [
        {
            "entity_id": s.get("entity_id"),
            "friendly_name": (s.get("attributes") or {}).get("friendly_name"),
            "state": s.get("state"),
        }
        for s in data
    ]


def ha_resolve(name: str, domain: str | None = None, max_candidates: int = 5):
    """
    Resolve a human name like 'Nightstand' to likely entity_ids.
    Strategy: exact friendly_name, exact entity suffix, endswith, then fuzzy.
    """
    _ha_ok()
    cand = ha_list_states(domain)
    if domain is None:
        pri = ("light", "switch", "scene", "script", "cover", "climate", "media_player", "fan")
        cand = sorted(cand, key=lambda x: 0 if (x["entity_id"].split(".")[0] in pri) else 1)

    target_n = _norm(name)
    target_slug = _slug(name)

    scored = []
    for c in cand:
        ent = c["entity_id"]
        fr = c.get("friendly_name") or ""
        n_fr = _norm(fr)
        slug = ent.split(".", 1)[1] if "." in ent else ent

        if n_fr == target_n:
            score = 1.0
        elif slug == target_slug:
            score = 0.98
        elif slug.endswith(target_slug):
            score = 0.95
        else:
            score = max(
                difflib.SequenceMatcher(None, n_fr, target_n).ratio(),
                difflib.SequenceMatcher(None, slug, target_slug).ratio(),
            ) * 0.94

        scored.append(
            {
                "entity_id": ent,
                "friendly_name": fr,
                "score": round(score, 4),
                "state": c.get("state"),
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:max_candidates]
    best = top[0] if top else None
    return {"query": name, "domain": domain, "best": best, "candidates": top}


# ----------- WebSocket manager with live subscribe -----------
try:
    import websocket  # pip install websocket-client
except Exception:
    websocket = None


class _WS:
    def __init__(self, base_http: str, token: str, log_file: str):
        self.url = base_http.replace("http", "ws") + "/api/websocket"
        self.token = token
        self.log_file = log_file

        self.thread = None
        self.stop = threading.Event()

        # Desired filters (persist across reconnects)
        self.event_types = set()
        self.entity_ids = set()

        # Connection state
        self._ws = None
        self._lock = threading.Lock()
        self._msg_id = 0
        self._active_event_types = set()

    def _next_id(self):
        self._msg_id += 1
        return self._msg_id

    def _send(self, obj: dict):
        with self._lock:
            if not self._ws:
                raise RuntimeError("WS not connected yet")
            self._ws.send(json.dumps(obj))

    def start(self):
        if websocket is None:
            raise RuntimeError("websocket-client not installed")
        if self.thread and self.thread.is_alive():
            return
        self.stop.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def subscribe(self, event_types=None, entity_ids=None):
        """Update desired filters. If connected, immediately subscribe to new event_types."""
        new_types = set(event_types or [])
        new_entities = set(entity_ids or [])
        need_sub_types = set()

        with self._lock:
            for et in new_types:
                if et not in self.event_types:
                    self.event_types.add(et)
                    if et not in self._active_event_types and self._ws is not None:
                        need_sub_types.add(et)
            if new_entities:
                self.entity_ids.update(new_entities)

        for et in need_sub_types:
            try:
                self._send({"id": self._next_id(), "type": "subscribe_events", "event_type": et})
                with self._lock:
                    self._active_event_types.add(et)
            except Exception as e:
                print(f"[HA WS] subscribe({et}) failed now; will retry on reconnect: {e}")

        return {
            "status": "subscribed",
            "now_connected": self.is_connected(),
            "event_types": sorted(self.event_types or {"state_changed"}),
            "entity_ids": sorted(self.entity_ids),
        }

    def is_connected(self) -> bool:
        with self._lock:
            return self._ws is not None

    def _run(self):
        backoff = 1
        while not self.stop.is_set():
            ws = None
            try:
                ws = websocket.create_connection(
                    self.url, timeout=10, ping_interval=30, ping_timeout=10
                )
                with self._lock:
                    self._ws = ws
                    self._active_event_types.clear()

                # Auth
                msg = json.loads(ws.recv())
                if msg.get("type") != "auth_required":
                    raise RuntimeError("WS auth protocol mismatch")
                self._send({"type": "auth", "access_token": self.token})
                if json.loads(ws.recv()).get("type") != "auth_ok":
                    raise RuntimeError("WS auth failed")

                # Subscribe to desired (or default)
                with self._lock:
                    ets = list(self.event_types or {"state_changed"})
                for et in ets:
                    self._send({"id": self._next_id(), "type": "subscribe_events", "event_type": et})
                    with self._lock:
                        self._active_event_types.add(et)

                backoff = 1  # reset backoff on successful connect

                # Receive loop
                while not self.stop.is_set():
                    raw = ws.recv()
                    msg = json.loads(raw)

                    if msg.get("type") == "event":
                        ev = msg.get("event", {})
                        et = ev.get("event_type")
                        keep = True
                        if et == "state_changed":
                            with self._lock:
                                ents = set(self.entity_ids)
                            if ents:
                                ent = (ev.get("data") or {}).get("entity_id")
                                keep = ent in ents
                        if keep:
                            line = (
                                f"\n- [{datetime.now().isoformat(timespec='seconds')}] "
                                f"WS {et}: {json.dumps(ev)[:1500]}"
                            )
                            with open(os.path.expanduser("memory.md"), "a", encoding="utf-8") as f:
                                f.write(line)
                            print(line)

            except Exception as ex:
                print(f"[HA WS] reconnect in {backoff}s ({ex})")
                time.sleep(min(backoff, 15))
                backoff = min(backoff * 2, 30)
            finally:
                try:
                    if ws:
                        ws.close()
                except Exception:
                    pass
                with self._lock:
                    self._ws = None
                    self._active_event_types.clear()


# Singleton and tool wrappers
_ws = _WS(HA_BASE, HA_TOKEN, os.path.expanduser("memory.md"))


def _ws_subscribe(event_types=None, entity_ids=None):
    _ws.start()
    return _ws.subscribe(event_types or [], entity_ids or [])


def _ws_stop():
    _ws.stop.set()
    try:
        with _ws._lock:
            if _ws._ws:
                _ws._ws.close()
    except Exception:
        pass
    return {"status": "stopped"}


def _ws_status():
    return {
        "connected": _ws.is_connected(),
        "event_types": sorted(_ws.event_types or {"state_changed"}),
        "entity_ids": sorted(_ws.entity_ids),
    }


# ----------- Register tools -----------
register_tool(
    ToolSpec(
        name="ha_service",
        kind="function",
        description="Call any Home Assistant service (e.g., light.turn_on).",
        parameters={
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "service": {"type": "string"},
                "service_data": {"type": "object", "description": "Preferred payload object"},
                "data": {"type": "object", "description": "Alias for service_data; merged if provided"},
                "entity_id": {
                    "type": ["string", "array"],
                    "items": {"type": "string"},
                    "description": "Alias; placed into service_data.entity_id if provided",
                },
                "target": {
                    "type": "object",
                    "description": "Optional HA target: {entity_id|area_id|device_id}",
                    "properties": {
                        "entity_id": {"type": ["string", "array"], "items": {"type": "string"}},
                        "area_id": {"type": ["string", "array"], "items": {"type": "string"}},
                        "device_id": {"type": ["string", "array"], "items": {"type": "string"}},
                    },
                },
            },
            "required": ["domain", "service"],
        },
        runner=ha_service,
    )
)

register_tool(
    ToolSpec(
        name="ha_get_state",
        kind="function",
        description="Get state and attributes of a single entity_id.",
        parameters={"type": "object", "properties": {"entity_id": {"type": "string"}}, "required": ["entity_id"]},
        runner=ha_get_state,
    )
)

register_tool(
    ToolSpec(
        name="ha_fire_event",
        kind="function",
        description="Fire a custom event on HA's event bus.",
        parameters={
            "type": "object",
            "properties": {"event_type": {"type": "string"}, "event_data": {"type": "object"}},
            "required": ["event_type"],
        },
        runner=ha_fire_event,
    )
)

register_tool(
    ToolSpec(
        name="ha_template",
        kind="function",
        description="Render a Jinja template on the HA server.",
        parameters={"type": "object", "properties": {"template": {"type": "string"}}, "required": ["template"]},
        runner=ha_template,
    )
)

register_tool(
    ToolSpec(
        name="ha_health",
        kind="function",
        description="Check Home Assistant connectivity and summarize entity inventory.",
        parameters={"type": "object", "properties": {}},
        runner=ha_health,
    )
)

register_tool(
    ToolSpec(
        name="ha_list_states",
        kind="function",
        description="List entities (optionally filtered by domain).",
        parameters={"type": "object", "properties": {"domain": {"type": "string"}}},
        runner=ha_list_states,
    )
)

register_tool(
    ToolSpec(
        name="ha_resolve",
        kind="function",
        description="Resolve a natural device name to an entity_id, with fuzzy matching. Optionally hint a domain like 'light' or 'switch'.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "domain": {"type": "string"},
                "max_candidates": {"type": "integer", "minimum": 1, "maximum": 25},
            },
            "required": ["name"],
        },
        runner=ha_resolve,
    )
)

register_tool(
    ToolSpec(
        name="ha_ws_subscribe",
        kind="function",
        description="Subscribe to HA WS events; can be called repeatedly to add new event types and/or entity filters live.",
        parameters={
            "type": "object",
            "properties": {
                "event_types": {"type": "array", "items": {"type": "string"}},
                "entity_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
        runner=_ws_subscribe,
    )
)

register_tool(
    ToolSpec(
        name="ha_ws_stop",
        kind="function",
        description="Stop HA WebSocket listener.",
        parameters={"type": "object", "properties": {}},
        runner=_ws_stop,
    )
)

register_tool(
    ToolSpec(
        name="ha_ws_status",
        kind="function",
        description="Report WebSocket connection and current subscriptions.",
        parameters={"type": "object", "properties": {}},
        runner=_ws_status,
    )
)
