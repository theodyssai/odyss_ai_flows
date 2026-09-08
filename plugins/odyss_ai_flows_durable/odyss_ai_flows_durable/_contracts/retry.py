from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DurableRetryPolicy:
    attempts: int = 3
    backoff: float = 2.0
    jitter: float = 0.0
    initial_delay_seconds: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempts": self.attempts,
            "backoff": self.backoff,
            "jitter": self.jitter,
            "initial_delay_seconds": self.initial_delay_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DurableRetryPolicy":
        return cls(
            attempts=int(data.get("attempts", 3)),
            backoff=float(data.get("backoff", 2.0)),
            jitter=float(data.get("jitter", 0.0)),
            initial_delay_seconds=float(data.get("initial_delay_seconds", 1.0)),
        )
