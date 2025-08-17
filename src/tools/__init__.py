# src/tools/__init__.py
# Import tool modules so they register themselves with the registry at startup.
from .homeassistant import *  # noqa: F401,F403
from .sandbox import *        # noqa: F401,F403
