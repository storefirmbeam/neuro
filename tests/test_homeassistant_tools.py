# tests/test_homeassistant_tools.py
import uuid
import pytest

from src.tools.homeassistant import (  # type: ignore
    ha_health, ha_template, ha_get_state, ha_resolve, ha_service,
    _ws_subscribe, _ws_status, _ws_stop
)

@pytest.mark.integration
def test_health_smoke(ha_ready):
    h = ha_health()
    assert "version" in h
    assert isinstance(h.get("entities_total"), int)


@pytest.mark.integration
def test_template_eval(ha_ready):
    r = ha_template("{{ 2 + 2 }}")
    assert r["status"] == 200
    # HA returns rendered template in "json" as plain text
    out = r["json"]
    # Sometimes HA wraps it, but for simple templates it's just "4"
    assert "4" in str(out)


@pytest.mark.integration
def test_get_state_sun(ha_ready):
    # "sun.sun" is available in a default HA setup
    r = ha_get_state("sun.sun")
    assert r["status"] == 200
    j = r["json"]
    assert j.get("entity_id") == "sun.sun"
    assert "state" in j


@pytest.mark.integration
def test_resolve_sun(ha_ready):
    # Friendly name is "Sun"
    res = ha_resolve("Sun")
    best = res.get("best") or {}
    assert (best.get("entity_id") == "sun.sun") or (best.get("friendly_name") == "Sun")


@pytest.mark.integration
def test_ws_subscribe_and_service_call_logs_event(ha_ready, memory_path):
    # Subscribe live to "call_service" events
    out = _ws_subscribe(event_types=["call_service"])
    assert "call_service" in out["event_types"]

    # Wait until WS is connected and subscribed
    from tests.conftest import wait_for_ws, wait_for_log_contains  # reuse helpers
    status = wait_for_ws(event_types=["call_service"], timeout=12.0)
    assert status and status["connected"]

    # Trigger a service call that does not require an entity: persistent_notification.create
    marker = f"pytest-{uuid.uuid4()}"
    r = ha_service("persistent_notification", "create",
                   {"message": marker, "title": "pytest"})
    assert 200 <= r["status"] < 300

    # The WS manager writes events to memory.md; look for our marker
    assert wait_for_log_contains(memory_path, marker, timeout=12.0), \
        "Did not see call_service event with our marker in memory.md"

    # Clean up socket
    _ws_stop()
    # It's okay if stop is asynchronous; the test just ensures we called it.


