from __future__ import annotations

from typing import Any
from typing import Optional

from odyss_ai_flows.core.config.api import cget
from odyss_ai_flows.core.handlers.llm.components.base import (
    LLMHandlerComponent,
)
from odyss_ai_flows.core.utils.logger import logger
from odyss_ai_flows_openrouter.handlers.helpers.openrouter_client import (
    get_openrouter_client,
)
from odyss_ai_flows_openrouter.handlers.helpers.token_buffer import (
    get_node_stream_buffer,
)


def _unwrap(value: Any) -> Any:
    return value.unwrap() if hasattr(value, "unwrap") else value


async def _get_client_and_config() -> tuple[Any, dict]:
    key = await cget(
        "oai_connection_name",
        default="openrouter",
    )

    config = await cget(
        key,
        default={},
    )

    api_key = _unwrap(config.get("api_key"))

    if not api_key:
        raise RuntimeError(
            "OpenRouter connection profile missing 'api_key'"
        )

    client = get_openrouter_client(
        api_key=api_key,
        base_url=config.get("base_url"),
    )

    return client, config


_CONNECTION_FIELDS = frozenset({
    "api_key",
    "base_url",
    "model",
})


def _request_kwargs(
    cfg: dict,
) -> dict:
    parameters = {
        key: value
        for key, value in cfg.items()
        if key not in _CONNECTION_FIELDS
    }

    return (
        {"extra_body": parameters}
        if parameters
        else {}
    )


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


class OpenRouterCaller(LLMHandlerComponent):
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
                f"- Using OpenRouterCaller "
                f"(structured mode)"
            )

        else:
            logger.info(
                f"{self.handler.node.name} "
                f"- Using OpenRouterCaller "
                f"(text mode)"
            )

        client, cfg = await _get_client_and_config()

        model = cfg["model"]

        messages = self.handler.messages

        # -----------------------------------------------------
        # Structured mode
        # -----------------------------------------------------

        if model_cls:

            result = (
                await client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format=model_cls,
                    **_request_kwargs(cfg),
                )
            )

            self.handler.response = result

            parsed = _extract_parsed(
                result
            )

            if parsed is None:
                # Some OpenRouter models honor json_schema but return raw
                # JSON the SDK doesn't auto-parse; validate it ourselves.
                raw = _extract_text(result)

                if not raw:
                    raise RuntimeError(
                        f"{self.handler.node.name} "
                        f"- No structured response returned"
                    )

                parsed = model_cls.model_validate_json(raw)

            self.handler.structured = parsed

            return parsed

        # -----------------------------------------------------
        # Text mode
        # -----------------------------------------------------

        result = await client.chat.completions.create(
            model=model,
            messages=messages,
            **_request_kwargs(cfg),
        )

        self.handler.response = result

        text = _extract_text(result)

        return text


class OpenRouterCallerStreaming(
    LLMHandlerComponent
):
    async def run(
        self,
        _: Optional[str],
    ) -> str:

        logger.info(
            f"{self.handler.node.name} "
            f"- Using OpenRouterCallerStreaming"
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

        model = cfg["model"]

        messages = self.handler.messages

        buffer = get_node_stream_buffer(
            self.handler.node.name
        )

        content_parts: list[str] = []

        usage_chunk: Any = None

        try:
            stream = (
                await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                    stream_options={
                        "include_usage": True
                    },
                    **_request_kwargs(cfg),
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
