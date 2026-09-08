from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------
# Dispatch mode
# ---------------------------------------------------------

class DispatchMode(str, Enum):
    DURABLE = "durable"
    DIRECT  = "direct"


# ---------------------------------------------------------
# DurableFlowStep (single step / subflow definition)
# ---------------------------------------------------------

@dataclass(slots=True)
class DurableFlowStep:

    flow_name: str
    mode: DispatchMode = DispatchMode.DURABLE
    name: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    input_keys: list[str] | None = None
    output_keys: list[str] | None = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "flow_name": self.flow_name,
            "mode": self.mode.value,
            "name": self.name,
            "inputs": self.inputs,
            "input_keys": self.input_keys,
            "output_keys": self.output_keys,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DurableFlowStep":
        input_keys = data.get("input_keys")
        output_keys_raw = data.get("output_keys", [])

        return cls(
            flow_name=data["flow_name"],
            mode=DispatchMode(data.get("mode", DispatchMode.DURABLE.value)),
            name=data.get("name"),
            inputs=dict(data.get("inputs") or {}),
            input_keys=list(input_keys) if input_keys is not None else None,
            output_keys=list(output_keys_raw) if output_keys_raw is not None else None,
        )


# ---------------------------------------------------------
# DurableFlowPlan (container for multi-flow execution)
# ---------------------------------------------------------

class DurableFlowPlan:

    def __init__(self, steps: list[DurableFlowStep]) -> None:
        self._steps = list(steps)

    @property
    def steps(self) -> list[DurableFlowStep]:
        return self._steps

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": [step.to_dict() for step in self._steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DurableFlowPlan":
        return cls(
            steps=[DurableFlowStep.from_dict(s) for s in data.get("steps", [])],
        )


# ---------------------------------------------------------
# DurableSubflowGroupConfig (per-group dispatch behavior)
# ---------------------------------------------------------

@dataclass(slots=True)
class DurableSubflowGroupConfig:

    max_concurrent: int | None = None
    wait_before_seconds: float | None = None
    wait_after_seconds: float | None = None
    skip_group_output: bool | None = None

    def resolved(self, defaults: "DurableSubflowGroupConfig | None" = None) -> "DurableSubflowGroupConfig":
        defaults = defaults or DurableSubflowGroupConfig()

        return DurableSubflowGroupConfig(
            max_concurrent=self.max_concurrent if self.max_concurrent is not None else defaults.max_concurrent,
            wait_before_seconds=self.wait_before_seconds if self.wait_before_seconds is not None else (defaults.wait_before_seconds or 0.0),
            wait_after_seconds=self.wait_after_seconds if self.wait_after_seconds is not None else (defaults.wait_after_seconds or 0.0),
            skip_group_output=self.skip_group_output if self.skip_group_output is not None else bool(defaults.skip_group_output),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_concurrent": self.max_concurrent,
            "wait_before_seconds": self.wait_before_seconds,
            "wait_after_seconds": self.wait_after_seconds,
            "skip_group_output": self.skip_group_output,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DurableSubflowGroupConfig":
        return cls(
            max_concurrent=data.get("max_concurrent"),
            wait_before_seconds=data.get("wait_before_seconds"),
            wait_after_seconds=data.get("wait_after_seconds"),
            skip_group_output=data.get("skip_group_output"),
        )


# ---------------------------------------------------------
# DurableSubflowGroup (one stage of staged subflow dispatch)
# ---------------------------------------------------------

@dataclass(slots=True)
class DurableSubflowGroup:

    key: str
    steps: list[DurableFlowStep] = field(default_factory=list)
    config: DurableSubflowGroupConfig = field(default_factory=DurableSubflowGroupConfig)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "steps": [s.to_dict() for s in self.steps],
            "config": self.config.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DurableSubflowGroup":
        return cls(
            key=data["key"],
            steps=[DurableFlowStep.from_dict(s) for s in data.get("steps", [])],
            config=DurableSubflowGroupConfig.from_dict(data.get("config") or {}),
        )


# ---------------------------------------------------------
# DurableSubflowOutput (node return type that carries subflows)
# ---------------------------------------------------------

@dataclass(slots=True)
class DurableSubflowOutput:

    data: Any
    subflows: list[DurableFlowStep] = field(default_factory=list)
    groups: list[DurableSubflowGroup] = field(default_factory=list)
    default_group_config: DurableSubflowGroupConfig | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "_type": "DurableSubflowOutput",
            "data": self.data,
        }

        if self.subflows:
            d["subflows"] = [f.to_dict() for f in self.subflows]

        if self.groups:
            d["groups"] = [g.to_dict() for g in self.groups]

        if self.default_group_config is not None:
            d["default_group_config"] = self.default_group_config.to_dict()

        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DurableSubflowOutput":
        default_group_config = data.get("default_group_config")

        return cls(
            data=data.get("data"),
            subflows=[DurableFlowStep.from_dict(s) for s in data.get("subflows", [])],
            groups=[DurableSubflowGroup.from_dict(g) for g in data.get("groups", [])],
            default_group_config=(
                DurableSubflowGroupConfig.from_dict(default_group_config)
                if default_group_config is not None
                else None
            ),
        )

    @staticmethod
    def is_serialized(value: Any) -> bool:
        return isinstance(value, dict) and value.get("_type") == "DurableSubflowOutput"
