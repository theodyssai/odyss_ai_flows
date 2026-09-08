from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Union


ENV_LOCAL_FILENAME = ".env.local"

# Entry-point groups any LLM-handling provider registers under.
# Only consulted by the (discouraged) ``any_provider`` requirement.

PROVIDER_ENTRY_POINT_GROUPS = (
    "odyss_ai_flows.llm_components",
    "odyss_ai_flows.llm_pipelines",
)

DEFAULT_LLM_PLUGIN_DIST = "odyss_ai_flows_azure"

DEFAULT_LLM_PLUGIN_ENTRY_POINT = "call_azure"

DEFAULT_LLM_ENV_VARS = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_DEPLOYMENT",
)


# plugin -> hard prerequisite: a missing plugin means the scenario
#           cannot even import, so it is skipped in EVERY mode.
# config -> soft: skipped in auto/static, run-and-fail in --live so
#           nothing silently passes.

PLUGIN_AXIS = "plugin"

CONFIG_AXIS = "config"


@dataclass(slots=True)
class RequirementStatus:

    satisfied: bool

    detail: str


class Requirement:
    """One condition a scenario needs to run.

    Subclass and implement ``describe`` + ``check`` to add a new kind,
    or just use :func:`custom` / :func:`custom_check` for a one-off.
    """

    axis: str = CONFIG_AXIS

    def describe(self) -> str:
        raise NotImplementedError

    def check(
        self,
        scenario_dir: Path,
    ) -> RequirementStatus:
        raise NotImplementedError

    def suite_cache_key(self) -> str | None:
        """Return an explicit suite-planning cache key, if safe to share."""

        return None

CheckResult = Union[bool, tuple[bool, str], RequirementStatus]

CheckFn = Callable[..., CheckResult]
