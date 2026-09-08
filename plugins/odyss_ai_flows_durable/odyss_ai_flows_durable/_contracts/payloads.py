from __future__ import annotations

from dataclasses import asdict, dataclass

from typing import Any


@dataclass(slots=True)
class FlowOrchestrationInput:

    flow_name: str
    inputs: dict[str, Any]
    retry_policy: dict[str, Any] | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "FlowOrchestrationInput":
        return cls(
            flow_name=data["flow_name"],
            inputs=data.get("inputs") or {},
            retry_policy=data.get("retry_policy"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NodeOrchestrationInput:

    node: str
    flow_name: str
    base_inputs: dict[str, Any]
    upstream: list[str]
    downstream_instance_ids: dict[str, str]
    retry_policy: dict[str, Any] | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "NodeOrchestrationInput":
        return cls(
            node=data["node"],
            flow_name=data["flow_name"],
            base_inputs=data.get("base_inputs") or {},
            upstream=list(data.get("upstream") or []),
            downstream_instance_ids=dict(data.get("downstream_instance_ids") or {}),
            retry_policy=data.get("retry_policy"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NodeActivityInput:

    node: str
    flow_name: str
    base_inputs: dict[str, Any]
    dep_results: dict[str, Any]

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "NodeActivityInput":
        return cls(
            node=data["node"],
            flow_name=data["flow_name"],
            base_inputs=data.get("base_inputs") or {},
            dep_results=data.get("dep_results") or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SignalActivityInput:

    target_instance_id: str
    event_name: str
    data: Any

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "SignalActivityInput":
        return cls(
            target_instance_id=data["target_instance_id"],
            event_name=data["event_name"],
            data=data.get("data"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
