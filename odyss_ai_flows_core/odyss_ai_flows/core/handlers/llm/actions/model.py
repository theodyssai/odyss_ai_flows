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

from typing import Type

from pydantic import BaseModel


def make_model_func(handler):
    def model(
        model_class: Type[BaseModel],
        render_text: bool = True,
    ) -> str:

        # -----------------------------------------------------
        # Validate input
        # -----------------------------------------------------

        if not isinstance(model_class, type):
            raise TypeError(
                "model() expects a Pydantic model class"
            )

        if not issubclass(model_class, BaseModel):
            raise TypeError(
                "model() expects a subclass of pydantic.BaseModel"
            )

        # -----------------------------------------------------
        # Conflict detection
        # -----------------------------------------------------

        if getattr(
            handler,
            "static_model_class",
            None,
        ) is not None:

            raise RuntimeError(
                "Cannot use model() because a "
                "node:model structured output "
                "is already defined for this node"
            )

        if getattr(
            handler,
            "action_model_class",
            None,
        ) is not None:

            raise RuntimeError(
                "Cannot use model() because "
                "actions() already defined a "
                "structured output model"
            )

        existing_dynamic = getattr(
            handler,
            "dynamic_model_class",
            None,
        )

        if (
            existing_dynamic is not None
            and existing_dynamic is not model_class
        ):
            raise RuntimeError(
                "model() was called multiple times "
                "with different model classes"
            )

        # -----------------------------------------------------
        # Registration
        # -----------------------------------------------------

        handler.dynamic_model_class = model_class
        handler.model_class = model_class

        # -----------------------------------------------------
        # Prompt-visible rendering
        # -----------------------------------------------------

        if not render_text:
            return ""

        return (
            "Structured output format has been "
            "provided for this task.\n"
        )

    return model