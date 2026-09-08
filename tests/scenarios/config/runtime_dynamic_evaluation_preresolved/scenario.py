from __future__ import annotations

from pathlib import Path

from odyss_ai_flows.core.config.providers import (
    clear_providers,
    register_provider,
)

from odyss_ai_flows.core.config.resolver import (
    clear_semantic_template_cache,
)

from odyss_ai_flows.core.config.global_config import (
    pre_resolve_global_config_async,
    get_global_setting,
)

from odyss_ai_flows.core.config.utils import (
    SensitiveValue,
)

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from tests.tests_runtime.assertions import (
    assert_flow_success,
)


# =================================================
# Provider counters
# =================================================

provider_calls = {

    "ENV": 0,
    "VAULT": 0,
    "CONFIG": 0,
    "ASYNC_ADD": 0,
}


# =================================================
# Mock providers
# =================================================

async def ENV(key: str):

    provider_calls["ENV"] += 1

    values = {

        "MODE": "development",
    }

    return values.get(key)


async def VAULT(key: str):

    provider_calls["VAULT"] += 1

    return f"secret:{key}"


async def CONFIG(key: str):

    provider_calls["CONFIG"] += 1

    values = {

        "service_url": "https://service.local",
    }

    return values.get(key)


async def ASYNC_ADD(a, b):

    provider_calls["ASYNC_ADD"] += 1

    return a + b


# =================================================
# Scenario
# =================================================

async def run_scenario():

    clear_providers()
    clear_semantic_template_cache()

    # The real core SECRET wrapper marks any wrapped value sensitive.
    from odyss_ai_flows.core.config.providers import (
        SECRET,
    )

    register_provider(
        "ENV",
        ENV,
    )

    register_provider(
        "VAULT",
        VAULT,
        sensitive=True,
    )

    register_provider(
        "SECRET",
        SECRET,
        sensitive=True,
    )

    register_provider(
        "CONFIG",
        CONFIG,
    )

    register_provider(
        "ASYNC_ADD",
        ASYNC_ADD,
    )

    # =============================================
    # Global eager pre-resolution
    # =============================================

    await pre_resolve_global_config_async()

    # =============================================
    # Verify global eager resolution
    # =============================================

    secret = await get_global_setting(
        "secret_value"
    )

    assert isinstance(
        secret,
        SensitiveValue,
    )

    assert secret.unwrap() == (
        "secret:token"
    )

    # =============================================
    # Runtime eager flow execution
    # =============================================

    result = await run_flow(

        flow=Path(
            "area/flow"
        ),

        variant_paths=[

            Path(
                "variants/v1/flow"
            ),
        ],

        pre_resolve_config=True,
    )

    assert_flow_success(result)

    runtime = result["runtime_node"]

    # =============================================
    # Semantic equivalence
    # =============================================

    assert runtime["plain_string"] == (
        "hello"
    )

    assert runtime["jinja_math"] == 3

    assert runtime["env_mode"] == (
        "development"
    )

    assert runtime["config_url"] == (
        "https://service.local"
    )

    assert runtime["async_sum"] == 5

    assert runtime["ref_nested"] == (
        "final value"
    )

    assert runtime["dict_recursive"] == {

        "x": 2,
        "y": "development",
    }

    assert runtime["list_recursive"] == [

        4,
        "development",
    ]

    # =============================================
    # Sensitive values
    # =============================================

    secret = runtime["secret_value"]

    assert isinstance(
        secret,
        SensitiveValue,
    )

    assert secret.unwrap() == (
        "secret:token"
    )

    mixed = runtime["mixed_secret"]

    assert isinstance(
        mixed,
        SensitiveValue,
    )

    assert mixed.unwrap() == (
        "prefix:secret:token"
    )

    # =============================================
    # SECRET wrapper over an arbitrary source
    # =============================================

    wrapped_env = runtime["wrapped_env"]

    assert isinstance(
        wrapped_env,
        SensitiveValue,
    )

    assert wrapped_env.unwrap() == (
        "development"
    )

    # =============================================
    # Variant override
    # =============================================

    assert runtime["variant_value"] == (
        "variant override"
    )

    # =============================================
    # Cache reuse validation
    # =============================================

    #
    # Repeated expressions should not
    # repeatedly execute providers.
    #
    # We intentionally reuse ENV/SECRET
    # many times in config.
    #
