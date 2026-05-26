# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
from __future__ import annotations

from typing import Any
from typing import Optional

from odyss_ai_flows.core.config.api import cget
from odyss_ai_flows.core.handlers.llm.components.base import (
    LLMHandlerComponent,
)
from odyss_ai_flows.core.utils.logger import logger
from odyss_ai_flows_azure.handlers.helpers.azure_client import (
    get_azure_openai_client,
)
from odyss_ai_flows_azure.handlers.helpers.token_buffer import (
    get_node_stream_buffer,
)


async def _get_client_and_config() -> tuple[Any, dict]:
    key = await cget(
        "oai_connection_name",
        default="azure_openai",
    )

    config = await cget(
        key,
        default={},
    )

    client = get_azure_openai_client(
        config["endpoint"],
        config["api_version"],
        config.get("api_key"),
    )

    return client, config


def _inference_kwargs(
    cfg: dict,
) -> dict:

    return {
        "temperature": cfg.get(
            "temperature",
            1.0,
        ),

        "max_completion_tokens": cfg.get(
            "max_completion_tokens",
            800,
        ),

        "top_p": cfg.get(
            "top_p",
            1.0,
        ),
    }


def _extract_text(
    result: Any,
) -> str:

    content = (
        result.choices[0]
        .message
        .content
        if result.choices
        else ""
    )

    return (content or "").strip()


def _extract_parsed(
    result: Any,
) -> Any:

    return (
        result.choices[0]
        .message
        .parsed
        if result.choices
        else None
    )


class AzureCaller(LLMHandlerComponent):
    async def run(
        self,
        _: Optional[str],
    ) -> Any:

        model_cls = getattr(
            self.handler,
            "model_class",
            None,
        )

        if model_cls:
            logger.info(
                f"{self.handler.node.name} "
                f"- Using AzureCaller "
                f"(structured mode)"
            )

        else:
            logger.info(
                f"{self.handler.node.name} "
                f"- Using AzureCaller "
                f"(text mode)"
            )

        client, cfg = await _get_client_and_config()

        deployment = cfg[
            "deployment_name"
        ]

        messages = self.handler.messages

        # -----------------------------------------------------
        # Structured mode
        # -----------------------------------------------------

        if model_cls:

            result = (
                await client.beta.chat.completions.parse(
                    model=deployment,
                    messages=messages,
                    response_format=model_cls,
                    **_inference_kwargs(cfg),
                )
            )

            self.handler.response = result

            parsed = _extract_parsed(
                result
            )

            if parsed is None:
                raise RuntimeError(
                    f"{self.handler.node.name} "
                    f"- No parsed response returned"
                )

            self.handler.structured = parsed

            return parsed

        # -----------------------------------------------------
        # Text mode
        # -----------------------------------------------------

        result = await client.chat.completions.create(
            model=deployment,
            messages=messages,
            **_inference_kwargs(cfg),
        )

        self.handler.response = result

        text = _extract_text(result)

        return text


class AzureCallerStreaming(
    LLMHandlerComponent
):
    async def run(
        self,
        _: Optional[str],
    ) -> str:

        logger.info(
            f"{self.handler.node.name} "
            f"- Using AzureCallerStreaming"
        )

        if getattr(
            self.handler,
            "model_class",
            None,
        ):
            raise RuntimeError(
                f"{self.handler.node.name} "
                f"- Streaming structured output "
                f"is not supported yet"
            )

        client, cfg = await _get_client_and_config()

        deployment = cfg[
            "deployment_name"
        ]

        messages = self.handler.messages

        buffer = get_node_stream_buffer(
            self.handler.node.name
        )

        content_parts: list[str] = []

        usage_chunk: Any = None

        try:
            stream = (
                await client.chat.completions.create(
                    model=deployment,
                    messages=messages,
                    stream=True,
                    stream_options={
                        "include_usage": True
                    },
                    **_inference_kwargs(cfg),
                )
            )

            async for chunk in stream:

                has_choices = bool(
                    getattr(
                        chunk,
                        "choices",
                        None,
                    )
                )

                has_usage = (
                    getattr(
                        chunk,
                        "usage",
                        None,
                    )
                    is not None
                )

                if has_choices:
                    delta = getattr(
                        chunk.choices[0]
                        .delta,
                        "content",
                        None,
                    )

                    if delta:
                        content_parts.append(
                            delta
                        )

                        if buffer:
                            await buffer.write(
                                delta
                            )

                elif has_usage:
                    usage_chunk = chunk

                else:
                    continue

            if buffer:
                buffer.close()

            final_text = "".join(
                content_parts
            )

            self.handler.response = usage_chunk

            return final_text

        except Exception as e:
            if buffer:
                buffer.close()

            raise RuntimeError(
                f"Streaming failed in "
                f"'{self.handler.node.name}'"
            ) from e