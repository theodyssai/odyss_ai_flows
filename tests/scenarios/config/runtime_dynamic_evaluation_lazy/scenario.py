from __future__ import annotations

from pathlib import Path

from odyss_ai_flows.core.config.providers import (
    clear_providers,
    register_provider,
    get_providers,
)

from odyss_ai_flows.core.config.resolver import (
    clear_semantic_template_cache,
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
# Mock providers
# =================================================

async def ENV(key: str):

    values = {

        "MODE": "development",
        "HOST": "localhost",
    }

    return values.get(key)


async def SECRET(key: str):

    return f"secret:{key}"


async def CONFIG(key: str):

    values = {

        "service_url": "https://service.local",
    }

    return values.get(key)


async def ASYNC_ADD(a, b):

    return a + b


def UPPER(value):

    return value.upper()


# =================================================
# Scenario
# =================================================

async def run_scenario():

    clear_providers()
    clear_semantic_template_cache()

    register_provider(
        "ENV",
        ENV,
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

    register_provider(
        "UPPER",
        UPPER,
    )

    assert "ENV" in get_providers()
    assert "SECRET" in get_providers()

    result = await run_flow(

        flow=Path(
            "area/flow"
        ),

        variant_paths=[

            Path(
                "variants/v1/flow"
            ),
        ],
    )

    assert_flow_success(result)

    runtime = result["runtime_node"]

    # =================================================
    # Plain values
    # =================================================

    assert runtime["plain_string"] == "hello"
    assert runtime["plain_number"] == 123

    # =================================================
    # Jinja rendering
    # =================================================

    assert runtime["jinja_math"] == 3
    assert runtime["jinja_string"] == "hello world"

    # =================================================
    # Providers
    # =================================================

    assert runtime["env_mode"] == "development"

    assert runtime["config_url"] == (
        "https://service.local"
    )

    assert runtime["async_sum"] == 5

    assert runtime["upper"] == "HELLO"

    # =================================================
    # REF
    # =================================================

    assert runtime["ref_simple"] == (
        "base value"
    )

    assert runtime["ref_nested"] == (
        "final value"
    )

    # =================================================
    # Recursive structures
    # =================================================

    assert runtime["dict_recursive"] == {

        "x": 2,
        "y": "development",
    }

    assert runtime["list_recursive"] == [

        4,
        "development",
    ]

    # =================================================
    # Sensitive values
    # =================================================

    secret = runtime["secret_value"]

    assert isinstance(
        secret,
        SensitiveValue,
    )

    assert str(secret) == (
        SensitiveValue.PLACEHOLDER
    )

    assert secret.unwrap() == (
        "secret:token"
    )

    mixed = runtime["mixed_secret"]

    assert isinstance(
        mixed,
        SensitiveValue,
    )
    
    assert str(mixed) == (
        SensitiveValue.PLACEHOLDER
    )

    assert mixed.unwrap() == (
        "prefix:secret:token"
    )

    # =================================================
    # Variant override
    # =================================================

    assert runtime["variant_value"] == (
        "variant override"
    )