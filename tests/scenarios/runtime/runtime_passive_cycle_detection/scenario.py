from __future__ import annotations

import logging

from odyss_ai_flows.core.runtime.runner import run_flow
from odyss_ai_flows.core.executor.exceptions import CycleDetectedError
from odyss_ai_flows.core.utils.logger import logger


_PASSIVE_WARNING_MARKER = "Possible dependency cycle"

_PASSIVE_OFF = {
    "name": "",
    "path": ".",
    "config": {"execution": {"passive_cycle_detection": False}},
    "children": {},
}


class _WarningCapture(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno == logging.WARNING:
            self.messages.append(record.getMessage())


def _capture_warnings() -> _WarningCapture:
    handler = _WarningCapture()
    logger.addHandler(handler)
    return handler


def _stop_capture(handler: _WarningCapture) -> None:
    logger.removeHandler(handler)


def _passive_warnings(handler: _WarningCapture) -> list[str]:
    return [m for m in handler.messages if _PASSIVE_WARNING_MARKER in m]


async def run_scenario():

    logger.info("=== PASSIVE CYCLE DETECTION SCENARIO START ===")

    # =================================================
    # Direct 2-node cycle — passive warns by default, runtime still raises
    # =================================================

    capture = _capture_warnings()
    try:
        await run_flow("direct_cycle_flow", raise_on_fail=False)
        raise AssertionError("Expected CycleDetectedError")
    except CycleDetectedError:
        pass
    finally:
        _stop_capture(capture)

    warnings = _passive_warnings(capture)
    assert warnings, "Expected a passive cycle warning for direct_cycle_flow"
    assert any("a" in w and "b" in w for w in warnings), (
        f"Warning should mention nodes 'a' and 'b', got: {warnings}"
    )
    logger.info("[direct] passive warnings=%r", warnings)

    # =================================================
    # Indirect 3-node cycle — passive warns with all nodes
    # =================================================

    capture = _capture_warnings()
    try:
        await run_flow("indirect_cycle_flow", raise_on_fail=False)
        raise AssertionError("Expected CycleDetectedError")
    except CycleDetectedError:
        pass
    finally:
        _stop_capture(capture)

    warnings = _passive_warnings(capture)
    assert warnings, "Expected a passive cycle warning for indirect_cycle_flow"
    combined = " ".join(warnings)
    assert "a" in combined and "b" in combined and "c" in combined, (
        f"Warning should mention nodes 'a', 'b', 'c', got: {warnings}"
    )
    logger.info("[indirect] passive warnings=%r", warnings)

    # =================================================
    # Linear flow (b depends on a) — no cycle, no warning
    # =================================================

    capture = _capture_warnings()
    try:
        result = await run_flow("linear_flow")
    finally:
        _stop_capture(capture)

    assert not _passive_warnings(capture), (
        f"Expected no passive warning for linear_flow, got: {_passive_warnings(capture)}"
    )
    assert result["b"] == 2
    logger.info("[linear] no warnings, result=%r", result["b"])

    # =================================================
    # Passive disabled via config — no passive warning even on a real cycle
    # =================================================

    capture = _capture_warnings()
    try:
        await run_flow("direct_cycle_flow", provided_tree=_PASSIVE_OFF, raise_on_fail=False)
        raise AssertionError("Expected CycleDetectedError")
    except CycleDetectedError:
        pass
    finally:
        _stop_capture(capture)

    assert not _passive_warnings(capture), (
        "Expected no passive warning when execution.passive_cycle_detection is false"
    )
    logger.info("[disabled] no passive warnings as expected")

    # =================================================
    # Dynamic nget (variable) — passive does not detect it,
    # runtime still does
    # =================================================

    capture = _capture_warnings()
    try:
        await run_flow("dynamic_nget_flow", raise_on_fail=False)
        raise AssertionError("Expected CycleDetectedError")
    except CycleDetectedError:
        pass
    finally:
        _stop_capture(capture)

    assert not _passive_warnings(capture), (
        "Expected no passive warning for dynamic nget (variable, not string literal)"
    )
    logger.info("[dynamic] no passive warnings as expected")

    logger.info("=== PASSIVE CYCLE DETECTION SCENARIO END ===")
