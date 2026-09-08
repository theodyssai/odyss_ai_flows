# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
import contextvars
from typing import Optional

# Execution-scoped latch context variable
_current_latch: contextvars.ContextVar["FailureLatch"] = contextvars.ContextVar(
    "failure_latch"
)


def get_latch() -> "FailureLatch":
    """Return the current execution-scoped FailureLatch."""
    return _current_latch.get()


class FailureLatch:
    """
    Stores the first exception claimed during an execution.
    - Only one exception is ever recorded (first-wins).
    - No node name or traceback is stored here; the exception itself carries that context.
    """

    def __init__(self) -> None:
        self._exception: Optional[BaseException] = None

    def is_set(self) -> bool:
        """True if some exception has already been claimed."""
        return self._exception is not None

    def claim(self, exc: BaseException) -> bool:
        """
        Attempt to record the first exception.
        Returns True if this call won the race (latch was empty), False otherwise.
        """
        if self._exception is not None:
            return False
        self._exception = exc
        return True

    def get(self) -> Optional[BaseException]:
        """Return the latched exception, or None if nothing has been claimed."""
        return self._exception
