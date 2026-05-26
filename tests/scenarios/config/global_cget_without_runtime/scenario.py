from __future__ import annotations

import os

from odyss_ai_flows.core.utils.logger import (
    logger,
)

from odyss_ai_flows.core.config.api import (
    cget,
)

from odyss_ai_flows.core.config.global_config import (
    pre_resolve_global_config_async,
)

from odyss_ai_flows.core.config.providers import (
    clear_providers,
    register_provider,
)

from odyss_ai_flows.core.config.utils import (
    SensitiveValue,
)


# -------------------------------------------------
# Mock providers
# -------------------------------------------------

async def MOCK_SECRET(key: str):

    logger.info(
        "[MOCK_SECRET] resolving key=%r",
        key,
    )

    return f"secret::{key}"


async def MOCK_CONFIG(key: str):

    logger.info(
        "[MOCK_CONFIG] resolving key=%r",
        key,
    )

    return f"config::{key}"


# -------------------------------------------------
# Scenario
# -------------------------------------------------

async def run_scenario():

    logger.info(
        "=== GLOBAL CGET WITHOUT RUNTIME START ==="
    )

    # =============================================
    # Setup
    # =============================================

    os.environ["GLOBAL_TEST_ENV"] = (
        "env_value"
    )

    clear_providers()

    from odyss_ai_flows.core.config.providers import (
        ENV,
        LITERAL_SECRET,
    )

    register_provider(
        "ENV",
        ENV,
    )

    register_provider(
        "LITERAL_SECRET",
        LITERAL_SECRET,
        sensitive=True,
    )

    register_provider(
        "SECRET",
        MOCK_SECRET,
        sensitive=True,
    )

    register_provider(
        "CONFIG",
        MOCK_CONFIG,
    )

    logger.info(
        "Providers registered."
    )

    # =============================================
    # Lazy global resolution
    # =============================================

    logger.info(
        "=== LAZY GLOBAL RESOLUTION ==="
    )

    plain = await cget(
        "plain_value"
    )

    logger.info(
        "plain_value -> %r (%s)",
        plain,
        type(plain).__name__,
    )

    env_value = await cget(
        "env_value"
    )

    logger.info(
        "env_value -> %r (%s)",
        env_value,
        type(env_value).__name__,
    )

    config_value = await cget(
        "config_value"
    )

    logger.info(
        "config_value -> %r (%s)",
        config_value,
        type(config_value).__name__,
    )

    secret = await cget(
        "secret_value"
    )

    logger.info(
        "secret_value -> %r (%s)",
        secret,
        type(secret).__name__,
    )

    if isinstance(secret, SensitiveValue):

        logger.info(
            "secret_value.unwrap() -> %r",
            secret.unwrap(),
        )

    merged = await cget(
        "merged_dict"
    )

    logger.info(
        "merged_dict -> %r (%s)",
        merged,
        type(merged).__name__,
    )

    # =============================================
    # Assertions
    # =============================================

    assert plain == "plain"

    assert env_value == "env_value"

    assert config_value == "config::abc"

    assert isinstance(
        secret,
        SensitiveValue,
    )

    assert secret.unwrap() == (
        "secret::token"
    )

    assert merged == {

        "a": 1,

        "b": {

            "x": 2,
        },
    }

    # =============================================
    # Eager mode
    # =============================================

    logger.info(
        "=== PRE-RESOLVE GLOBAL CONFIG ==="
    )

    await pre_resolve_global_config_async()

    logger.info(
        "Pre-resolve complete."
    )

    secret2 = await cget(
        "secret_value"
    )

    logger.info(
        "secret_value (eager) -> %r (%s)",
        secret2,
        type(secret2).__name__,
    )

    assert isinstance(
        secret2,
        SensitiveValue,
    )

    assert secret2.unwrap() == (
        "secret::token"
    )

    logger.info(
        "=== GLOBAL CGET WITHOUT RUNTIME END ==="
    )