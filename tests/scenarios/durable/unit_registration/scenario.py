from __future__ import annotations

from unittest.mock import patch

import odyss_ai_flows_durable._telemetry.config as tconfig
import odyss_ai_flows_durable._telemetry.virtual_span as vspan
from odyss_ai_flows_durable import (
    DIRECT_FLOW_ACTIVITY,
    FLOW_ORCHESTRATOR,
    NODE_ACTIVITY,
    NODE_ORCHESTRATOR,
    PARALLEL_ORCHESTRATOR,
    SEQUENCE_ORCHESTRATOR,
    SIGNAL_ACTIVITY,
    SUBFLOWS_ORCHESTRATOR,
    VIRTUAL_SPAN_ACTIVITY,
    register_durable_support,
)
from odyss_ai_flows_durable._contracts.constants import JITTER_ACTIVITY
from odyss_ai_flows_durable._runtime._single.handlers import get_jitter_factor_activity
from odyss_ai_flows_durable._telemetry.config import is_telemetry_enabled
from odyss_ai_flows_durable._telemetry.virtual_span import build_virtual_span

from tests.scenarios.durable._shared.host_probe import (
    is_expected_function_registration,
    is_expected_host_health,
)


class _FakeBlueprint:
    """Records orchestrator/activity names registered via the df.Blueprint decorators."""

    def __init__(self) -> None:
        self.orchestrations: list[str] = []
        self.activities: list[str] = []
        self.orchestration_functions: dict[str, object] = {}
        self.activity_functions: dict[str, object] = {}

    def orchestration_trigger(self, *, context_name=None, orchestration=None):
        self.orchestrations.append(orchestration)

        def decorator(fn):
            self.orchestration_functions[orchestration] = fn
            return fn

        return decorator

    def activity_trigger(self, *, input_name=None, activity=None):
        self.activities.append(activity)

        def decorator(fn):
            self.activity_functions[activity] = fn
            return fn

        return decorator


class _RecordingEventClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, object]] = []

    async def raise_event(self, instance_id, event_name, data) -> None:
        self.calls.append((instance_id, event_name, data))


class _FakeSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, object] = {}

    def set_attribute(self, key, value) -> None:
        self.attributes[key] = value


class _FakeSpanContext:
    def __init__(self, span: _FakeSpan) -> None:
        self.span = span

    def __enter__(self):
        return self.span

    def __exit__(self, *exc):
        return False


class _FakeTracer:
    def __init__(self) -> None:
        self.span = _FakeSpan()
        self.calls: list[tuple[str, object, object]] = []

    def start_as_current_span(self, name, *, context=None, kind=None):
        self.calls.append((name, context, kind))
        return _FakeSpanContext(self.span)


class _FakePropagator:
    def __init__(self) -> None:
        self.extracted = None

    def extract(self, carrier):
        self.extracted = dict(carrier)
        return "parent-context"

    def inject(self, carrier) -> None:
        carrier["traceparent"] = "child-traceparent"


def _stub_setting(value):
    async def _get(key, default=None):
        return value
    return _get


async def run_scenario() -> None:
    # === Test-host identity contract =============================================
    health = {
        "service": "odyss-ai-flows-durable-test-host",
        "orchestrators": [FLOW_ORCHESTRATOR],
    }
    assert is_expected_host_health(200, health) is True
    assert is_expected_host_health(404, health) is False
    assert is_expected_host_health(200, {**health, "service": "other-host"}) is False
    assert is_expected_host_health(200, {**health, "orchestrators": []}) is False
    assert is_expected_host_health(200, {**health, "orchestrators": None}) is False

    registration = {
        "name": FLOW_ORCHESTRATOR,
        "config": {
            "bindings": [{
                "type": "orchestrationTrigger",
                "orchestration": FLOW_ORCHESTRATOR,
            }],
        },
    }
    assert is_expected_function_registration(200, registration) is True
    assert is_expected_function_registration(404, registration) is False
    assert is_expected_function_registration(
        200,
        {**registration, "name": "other_orchestrator"},
    ) is False
    assert is_expected_function_registration(
        200,
        {**registration, "config": {"bindings": []}},
    ) is False

    # === register_durable_support wires the full function set onto a Blueprint =====
    # A supplied DurableEventClient is captured by the registered signal Activity.
    bp = _FakeBlueprint()
    event_client = _RecordingEventClient()
    register_durable_support(bp, event_client=event_client)

    assert set(bp.orchestrations) == {
        FLOW_ORCHESTRATOR, NODE_ORCHESTRATOR, SUBFLOWS_ORCHESTRATOR,
        SEQUENCE_ORCHESTRATOR, PARALLEL_ORCHESTRATOR,
    }, bp.orchestrations
    assert set(bp.activities) == {
        NODE_ACTIVITY, SIGNAL_ACTIVITY, JITTER_ACTIVITY,
        DIRECT_FLOW_ACTIVITY, VIRTUAL_SPAN_ACTIVITY,
    }, bp.activities
    # Each shared function is registered exactly once (no duplicates).
    assert len(bp.orchestrations) == len(set(bp.orchestrations)) == 5, bp.orchestrations
    assert len(bp.activities) == len(set(bp.activities)) == 5, bp.activities

    await bp.activity_functions[SIGNAL_ACTIVITY]({
        "target_instance_id": "child-1",
        "event_name": "dep:producer",
        "data": {"result": 42},
    })
    assert event_client.calls == [
        ("child-1", "dep:producer", {"result": 42})
    ]

    # === Telemetry gating =======================================================
    with patch.object(tconfig, "get_global_setting", _stub_setting(False)):
        assert await is_telemetry_enabled() is False
        # Off: build_virtual_span is a replay-safe no-op that echoes traceparent (no span).
        assert await build_virtual_span({"_traceparent": "tp-123"}) == {"traceparent": "tp-123"}
        assert await build_virtual_span({}) == {"traceparent": None}
    with patch.object(tconfig, "get_global_setting", _stub_setting("yes")):
        assert await is_telemetry_enabled() is True   # truthy non-bool -> True

    # Enabled virtual spans preserve the parent, attach attributes, and inject the
    # child traceparent returned to the next orchestration level.
    async def _enabled():
        return True

    fake_tracer = _FakeTracer()
    fake_propagator = _FakePropagator()
    with patch.object(vspan, "is_telemetry_enabled", _enabled), \
         patch.object(vspan, "get_tracer", lambda name: fake_tracer), \
         patch.object(vspan, "propagator", fake_propagator):
        virtual = await build_virtual_span({
            "_traceparent": "parent-traceparent",
            "span_name": "durable.test",
            "attributes": {"durable.depth": 2},
        })

    assert virtual == {"traceparent": "child-traceparent"}
    assert fake_propagator.extracted == {"traceparent": "parent-traceparent"}
    assert fake_tracer.calls[0][0] == "durable.test"
    assert fake_tracer.calls[0][1] == "parent-context"
    assert fake_tracer.span.attributes == {"durable.depth": 2}

    # === Jitter activity: bounds + defensive coercion ===========================
    assert get_jitter_factor_activity(0.0) == 0.0
    assert get_jitter_factor_activity(-1.0) == 0.0            # non-positive -> 0.0
    assert get_jitter_factor_activity("not a number") == 0.0  # non-numeric -> 0.0
    for _ in range(200):
        v = get_jitter_factor_activity(0.5)
        assert 0.0 <= v < 0.5, v
