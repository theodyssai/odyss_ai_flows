from .config import is_telemetry_enabled
from .tracer import get_tracer, propagator
from .virtual_span import build_virtual_span

__all__ = [
    "build_virtual_span",
    "get_tracer",
    "is_telemetry_enabled",
    "propagator",
]
