from __future__ import annotations

# =============================================================
# Showcase + test for scenario requirement definitions.
#
# Core-only (declares no requirements of its own) so it always runs.
# It builds the same requirement bundles a real plugin scenario would
# put in its requirements.py, then drives the planner in-process to
# prove the skip/run decisions — without leaving a permanently-skipped
# scenario in the suite.
# =============================================================

from pathlib import Path

from tests.tests_runtime.discovery import discover_scenarios
from tests.tests_runtime.models import (
    ScenarioDefinition,
)

from tests.tests_runtime.mode import (
    TestMode,
    build_suite_plan,
)

from tests.tests_runtime.requirements import (
    CONFIG_AXIS,
    PLUGIN_AXIS,
    CustomRequirement,
    PluginRequirement,
    Requirement,
    RequirementStatus,
    azure,
    coerce_requirements,
    custom,
    custom_check,
    env,
    plugin,
    requires,
)


HERE = Path(__file__).parent


# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------

def _synthetic(reqs, name: str) -> ScenarioDefinition:

    return ScenarioDefinition(
        id=f"synthetic/{name}",
        name=name,
        group="synthetic",
        relative_path=Path("synthetic") / name,
        path=HERE,
        scenario_file=HERE / "scenario.py",
        requirements=list(reqs),
    )


def _plan(reqs, mode: TestMode, name: str = "s"):

    definition = _synthetic(reqs, name)

    return build_suite_plan(
        [definition],
        mode,
    ).plans[0]


# -------------------------------------------------------------
# 1. Showcase — the per-plugin definitions a scenario would ship
# -------------------------------------------------------------

def _showcase_definitions() -> dict[str, list[Requirement]]:

    return {
        # one-liner preset: plugin + its env vars
        "openrouter": requires().provider(
            "odyss_ai_flows_openrouter",
            "OPENROUTER_API_KEY",
            entry_point="call_openrouter",
        ),
        "anthropic": requires().provider(
            "odyss_ai_flows_anthropic",
            "ANTHROPIC_API_KEY",
            entry_point="call_anthropic",
        ),
        # several env vars
        "openai": requires().provider(
            "odyss_ai_flows_openai",
            "OPENAI_API_KEY",
            "OPENAI_ORG_ID",
            entry_point="call_openai",
        ),
        # explicit chain targeting a streaming entry point
        "openrouter_streaming": (
            requires()
            .plugin(
                "odyss_ai_flows_openrouter",
                entry_point="call_openrouter_streaming",
            )
            .env("OPENROUTER_API_KEY")
            .env("OPENROUTER_BASE_URL", consult_env_local=True)
        ),
        # local server: plugin installed + reachable (no API key)
        "vllm": (
            requires()
            .plugin("odyss_ai_flows_vllm", entry_point="call_vllm")
            .command("curl", "-fsS", "http://localhost:8000/health")
        ),
        # provider + external dependency probe
        "openrouter_redis": (
            requires()
            .provider(
                "odyss_ai_flows_openrouter",
                "OPENROUTER_API_KEY",
                entry_point="call_openrouter",
            )
            .command("redis-cli", "ping")
        ),
        # pin the pipelines entry-point group
        "azure_pipeline": requires().plugin(
            "odyss_ai_flows_azure",
            entry_point="azure",
            group="odyss_ai_flows.llm_pipelines",
        ),
        # Azure + a Functions host probe
        "azure_with_host": requires().azure().command("func", "--version"),
        # tier-2, provider-agnostic
        "any": requires().any_provider(),
    }


def _assert_showcase() -> int:

    defs = _showcase_definitions()

    for name, reqs in defs.items():

        assert reqs, name

        assert all(
            isinstance(r, Requirement)
            for r in reqs
        ), name

        # every bundle leads with a plugin-axis requirement
        assert reqs[0].axis == PLUGIN_AXIS, name

    # the preset is exactly plugin + env
    orr = defs["openrouter"]

    assert len(orr) == 2

    assert orr[0].describe() == (
        "plugin 'odyss_ai_flows_openrouter' "
        "(entry point 'call_openrouter')"
    )

    assert orr[1].axis == CONFIG_AXIS

    # azure() preset == plugin + the 4 env vars
    az = requires().azure()

    assert len(az) == 2

    assert az[0].axis == PLUGIN_AXIS and az[1].axis == CONFIG_AXIS

    return len(defs)


# -------------------------------------------------------------
# 2. Builder is a real list + coercion accepts every shape
# -------------------------------------------------------------

def _assert_builder_and_coercion() -> None:

    built = (
        requires()
        .plugin("odyss_ai_flows_azure", entry_point="call_azure")
        .env("A", "B")
        .command("true")
        .check("inline ok", lambda sd: True)
    )

    assert isinstance(built, list)

    assert [r.axis for r in built] == [
        PLUGIN_AXIS,
        CONFIG_AXIS,
        CONFIG_AXIS,
        CONFIG_AXIS,
    ]

    # coerce_requirements normalises all supported exports
    assert coerce_requirements(None) == []

    assert len(coerce_requirements(plugin("x"))) == 1          # single

    assert len(coerce_requirements(azure)) == 2               # callable

    assert len(coerce_requirements([azure(), env("A")])) == 3  # nested flatten

    assert len(coerce_requirements(built)) == 4               # builder/list


# -------------------------------------------------------------
# 3. Custom checks normalise every return shape; never crash
# -------------------------------------------------------------

def _raiser(scenario_dir):
    raise RuntimeError("boom")


def _assert_custom_checks() -> None:

    assert custom(lambda sd: True, "bool").check(HERE).satisfied is True

    tuple_status = custom(
        lambda sd: (False, "down"),
        "tuple",
    ).check(HERE)

    assert tuple_status.satisfied is False
    assert tuple_status.detail == "down"

    status_passthrough = custom(
        lambda sd: RequirementStatus(True, "explicit"),
        "status",
    ).check(HERE)

    assert status_passthrough.detail == "explicit"

    # zero-arg check functions are supported
    assert custom(lambda: True, "noarg").check(HERE).satisfied is True

    # a raising check is reported as unmet, not propagated
    raised = custom(_raiser, "raises").check(HERE)

    assert raised.satisfied is False
    assert "raised" in raised.detail

    # decorator form + custom axis
    @custom_check("decorated", axis=PLUGIN_AXIS)
    def decorated(scenario_dir):
        return True

    assert isinstance(decorated, CustomRequirement)
    assert decorated.axis == PLUGIN_AXIS
    assert decorated.check(HERE).satisfied is True


# -------------------------------------------------------------
# 4. Planner — the actual skip/run decisions per mode
# -------------------------------------------------------------

def _assert_planner() -> None:

    # no requirements -> always runs
    for mode in TestMode:
        assert _plan([], mode, "core").run is True

    # missing plugin -> hard prerequisite, skipped in EVERY mode
    missing_plugin = requires().plugin(
        "odyss_ai_flows_definitely_not_installed",
        entry_point="nope",
    )

    for mode in TestMode:
        p = _plan(missing_plugin, mode, "noplugin")
        assert p.run is False, mode
        assert "missing" in (p.skip_reason or "")

    # missing config (env) -> soft: skip auto/static, run-and-fail live
    missing_env = requires().env("ODYSS_FAKE_ENV_VAR_NOT_SET_XYZ")

    assert _plan(missing_env, TestMode.AUTO, "noenv").run is False
    assert _plan(missing_env, TestMode.STATIC, "noenv").run is False
    assert _plan(missing_env, TestMode.LIVE, "noenv").run is True

    # satisfied config -> runs in auto/live; static skips ALL req-bearing
    satisfied = requires().check("always ok", lambda sd: True)

    assert _plan(satisfied, TestMode.AUTO, "ok").run is True
    assert _plan(satisfied, TestMode.STATIC, "ok").run is False
    assert _plan(satisfied, TestMode.LIVE, "ok").run is True


# -------------------------------------------------------------
# 5. Every plugin scenario declares its hard prerequisites
# -------------------------------------------------------------

def _expected_plugin_distributions(scenario_id: str) -> set[str]:

    if scenario_id.startswith("azure_handlers/"):
        return {"odyss_ai_flows_azure"}

    if scenario_id.startswith("cache/"):
        return {"odyss_ai_flows_cache"}

    if scenario_id.startswith("durable/"):
        return {"odyss_ai_flows_durable"}

    if scenario_id.startswith("artifacts_"):
        return {"odyss_ai_flows_artifacts"}

    if scenario_id == "token_limiter":
        return {"odyss_ai_flows_token_limiter"}

    if scenario_id == "token_limiter_live":
        return {
            "odyss_ai_flows_token_limiter",
            "odyss_ai_flows_azure",
        }

    return set()


def _assert_plugin_scenario_requirements() -> int:

    checked = 0

    for scenario in discover_scenarios():

        expected = _expected_plugin_distributions(
            scenario.id
        )

        if not expected:
            continue

        sidecar = scenario.path / "requirements.py"

        assert sidecar.is_file(), (
            f"{scenario.id} exercises a plugin but has no "
            f"requirements.py"
        )

        declared = {
            req.dist
            for req in scenario.requirements
            if isinstance(req, PluginRequirement)
        }

        assert expected.issubset(declared), (
            f"{scenario.id} must declare {sorted(expected)}, "
            f"got {sorted(declared)}"
        )

        checked += 1

    assert checked > 0

    return checked


# -------------------------------------------------------------
# Entry point
# -------------------------------------------------------------

async def run_scenario():

    showcased = _assert_showcase()

    _assert_builder_and_coercion()

    _assert_custom_checks()

    _assert_planner()

    plugin_scenarios = _assert_plugin_scenario_requirements()

    return {
        "showcased_definitions": showcased,
        "plugin_scenarios_checked": plugin_scenarios,
        "checks": "ok",
    }
