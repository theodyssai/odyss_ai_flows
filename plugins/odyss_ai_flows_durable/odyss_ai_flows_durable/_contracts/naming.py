from __future__ import annotations

from odyss_ai_flows_durable._contracts.constants import (
    DEPENDENCY_EVENT_PREFIX,
)


def dependency_event_name(node: str) -> str:
    return f"{DEPENDENCY_EVENT_PREFIX}{node}"


def build_child_instance_id(
    *,
    parent_instance_id: str | None,
    node: str,
) -> str:
    if parent_instance_id:
        return f"{parent_instance_id}_{node}"

    return node
