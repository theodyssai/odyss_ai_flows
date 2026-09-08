from __future__ import annotations

from collections.abc import MutableMapping

from opentelemetry.trace import SpanKind

from .config import is_telemetry_enabled
from .tracer import get_tracer, propagator


async def build_virtual_span(input_data: dict) -> dict:
    if not await is_telemetry_enabled():
        return {"traceparent": input_data.get("_traceparent")}

    parent_traceparent = input_data.get("_traceparent")
    parent_ctx = propagator.extract({"traceparent": parent_traceparent}) if parent_traceparent else None

    span_name = input_data.get("span_name", "durable.virtual")
    attributes = input_data.get("attributes") or {}
    carrier: MutableMapping[str, str] = {}

    with get_tracer(__name__).start_as_current_span(span_name, context=parent_ctx, kind=SpanKind.INTERNAL) as span:
        for k, v in attributes.items():
            span.set_attribute(k, v)
        propagator.inject(carrier)  # type: ignore[arg-type]

    return {"traceparent": carrier.get("traceparent", parent_traceparent)}
