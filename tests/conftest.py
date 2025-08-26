# tests/conftest.py
import os, sys, time, pathlib
import pytest
from dotenv import load_dotenv

# Make "src" importable (project root on PYTHONPATH)
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv()  # load HA_BASE_URL, HA_TOKEN from your .env at project root

# Import after sys.path tweak
from src.tools.homeassistant import ha_health, _ws_status  # type: ignore


@pytest.fixture(scope="session")
def memory_path():
    """Path to the log file used by the WS manager."""
    p = ROOT / "memory.md"
    p.touch(exist_ok=True)
    return p


@pytest.fixture(scope="session")
def ha_ready():
    """Skip all tests if HA is not reachable or token is missing."""
    try:
        h = ha_health()
        base = h.get("base")
        assert base, "Missing base URL"
        return True
    except Exception as e:
        pytest.skip(f"Home Assistant not reachable or token missing: {e}")


def wait_for_ws(event_types=None, timeout=10.0):
    """Poll WS status until connected and (optionally) subscribed to given types."""
    event_types = set(event_types or [])
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        last = _ws_status()
        if last.get("connected"):
            if not event_types or event_types.issubset(set(last.get("event_types", []))):
                return last
        time.sleep(0.25)
    return last


def wait_for_log_contains(memory_path, needle: str, timeout=8.0):
    """Wait until the memory.md contains needle."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            txt = memory_path.read_text(encoding="utf-8", errors="ignore")
            if needle in txt:
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False
