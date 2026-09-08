from __future__ import annotations

import textwrap

from tests.tests_runtime.assertions import (
    assert_flow_success,
)

from odyss_ai_flows.core.runtime.runner import (
    run_flow,
)

from odyss_ai_flows.core.runtime.prepared_flow import (
    PreparedFlow,
)

from odyss_ai_flows.core.runtime.flow_result import (
    SensitiveValue,
    unwrap,
)


REQUIRES_LLM = False


async def run_scenario():

    result = await run_flow(
        "area/flow",
    )

    assert_flow_success(
        result
    )

    # =====================================================
    # Export surface
    # =====================================================

    assert set(result.keys()) == {
        "secret_key",
        "plain_key",
    }

    # Filtered node absent
    assert "hidden_node" not in result

    # =====================================================
    # Sensitive value wrapped under mapped name
    # =====================================================

    secret = result[
        "secret_key"
    ]

    assert isinstance(
        secret,
        SensitiveValue,
    )

    assert secret.unwrap() == "s3cr3t-value"

    # =====================================================
    # Plain value passes through unwrap helper
    # =====================================================

    assert unwrap(
        result["plain_key"]
    ) == "plain-data"

    # =====================================================
    # Collection surfaces return wrappers
    # =====================================================

    assert isinstance(
        result.outputs["secret_key"],
        SensitiveValue,
    )

    assert isinstance(
        dict(result)["secret_key"],
        SensitiveValue,
    )

    assert isinstance(
        dict(result.items())["secret_key"],
        SensitiveValue,
    )

    assert any(
        isinstance(v, SensitiveValue)
        for v in result.values()
    )

    # =====================================================
    # Serialization redacts under mapped name
    # =====================================================

    json_text = result.to_json()

    assert "[REDACTED]" in json_text

    assert "s3cr3t-value" not in json_text

    assert "secret_key" in json_text

    assert "plain-data" in json_text

    # =====================================================
    # Logging surfaces redact
    # =====================================================

    assert "[REDACTED]" in str(result)

    assert "s3cr3t-value" not in str(result)

    assert "<SensitiveValue>" in repr(result.outputs)

    assert "s3cr3t-value" not in repr(result.outputs)

    # =====================================================
    # Raw graph preserves the underlying value
    # =====================================================

    assert (
        result.all_node_results["secret_node"]
        == "s3cr3t-value"
    )

    # =====================================================
    # Invalid spec: 'sensitive' must be a list
    # =====================================================

    invalid = (
        PreparedFlow()
        .fset(
            "producer.py",
            textwrap.dedent(
                '''
                from odyss_ai_flows import *

                @node
                async def producer():

                    return "value"
                '''
            ).strip(),
        )
        .fset(
            "outputs.json",
            textwrap.dedent(
                '''
                {
                    "include": [

                        "producer"
                    ],

                    "sensitive":
                        "producer"
                }
                '''
            ).strip(),
        )
    )

    try:

        await run_flow(
            invalid
        )

        raise AssertionError(
            "non-list 'sensitive' unexpectedly accepted"
        )

    except ValueError:
        pass
