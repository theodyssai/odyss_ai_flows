# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
from __future__ import annotations

import base64

from pathlib import Path
from typing import Optional
from typing import TYPE_CHECKING

from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import make_logging_undefined

from odyss_ai_flows.core.config.api import cget
from odyss_ai_flows.core.executor.api import nget

from odyss_ai_flows.core.handlers.llm.actions.jinja import (
    make_actions_func,
)
from odyss_ai_flows.core.handlers.llm.actions.model import (
    make_model_func,
)

from odyss_ai_flows.core.handlers.llm.components.base import (
    LLMHandlerComponent,
)

from odyss_ai_flows.core.handlers.llm.utils import (
    BufferedLogger,
)

from odyss_ai_flows.core.runtime.inputs import (
    iget,
)

if TYPE_CHECKING:
    from odyss_ai_flows.core.handlers.llm.composed_handler import (
        ComposedHandler,
    )


class SkipSignal(Exception):
    """Intentional early exit from rendering/execution."""
    pass


class PromptRenderer(LLMHandlerComponent):
    async def run(self, _: Optional[str]) -> str:

        def make_img_func(
            handler: "ComposedHandler",
        ):
            def img(path_or_url: str):

                if (
                    path_or_url.startswith(
                        "data:image"
                    )
                    or path_or_url.startswith(
                        "http"
                    )
                ):
                    handler.image_segments.append(
                        {
                            "image": path_or_url
                        }
                    )

                    return

                path = Path(path_or_url)

                if not path.exists():
                    raise FileNotFoundError(
                        f"Image path not found: "
                        f"{path_or_url}"
                    )

                b64 = base64.b64encode(
                    path.read_bytes()
                ).decode("utf-8")

                mime = (
                    "image/png"
                    if path.suffix.lower() == ".png"
                    else "image/jpeg"
                )

                handler.image_segments.append(
                    {
                        "image": (
                            f"data:{mime};base64,"
                            f"{b64}"
                        )
                    }
                )

            return img

        def make_skip_func():
            def skip(
                do_skip: bool = True,
            ):
                if do_skip:
                    raise SkipSignal()

            return skip

        node = self.handler.node

        # -----------------------------------------------------
        # Environment
        # -----------------------------------------------------

        env = Environment(
            enable_async=True,

            undefined=make_logging_undefined(
                logger=BufferedLogger(
                    name=(
                        f"tmpl_logger_"
                        f"{node.name}"
                    )
                )
            ),
        )

        env.globals.update({

            # ---------------------------------------------
            # Core helpers
            # ---------------------------------------------

            "iget": iget,
            "cget": cget,
            "nget": nget,

            # ---------------------------------------------
            # Utility helpers
            # ---------------------------------------------

            "img": make_img_func(
                self.handler
            ),

            "skip": make_skip_func(),

            # ---------------------------------------------
            # Structured output helpers
            # ---------------------------------------------

            "actions": make_actions_func(
                self.handler
            ),

            "model": make_model_func(
                self.handler
            ),
        })

        # -----------------------------------------------------
        # Template resolution
        # -----------------------------------------------------

        if node.content is not None:

            template = env.from_string(
                node.content
            )

        elif node.path is not None:

            env.loader = FileSystemLoader(
                node.path.parent
            )

            template = env.get_template(
                node.path.name
            )

        else:
            raise RuntimeError(
                f"PromptRenderer: node "
                f"'{node.name}' has no "
                f"template source"
            )

        # -----------------------------------------------------
        # Rendering
        # -----------------------------------------------------

        try:
            rendered = (
                await template.render_async()
            )

            self.handler.rendered_text = (
                rendered
            )

            return rendered

        except SkipSignal:
            self.handler._skipped = True
            return ""