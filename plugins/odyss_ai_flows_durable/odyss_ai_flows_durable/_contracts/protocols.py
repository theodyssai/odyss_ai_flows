from __future__ import annotations

from typing import Any, Protocol


class DurableEventClient(Protocol):

    async def raise_event(
        self,
        instance_id: str,
        event_name: str,
        data: Any,
    ) -> None:
        ...
