from __future__ import annotations

from opentelemetry import trace
from opentelemetry.propagate import get_global_textmap

propagator = get_global_textmap()


def get_tracer(name: str):
    return trace.get_tracer(name)
