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

from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import create_model
from pydantic import model_validator

from odyss_ai_flows.core.handlers.llm.actions.action import Action
from odyss_ai_flows.core.handlers.llm.actions.action import ExecutorMode


def build_actions_model(
    actions: list[Action],
    mode: ExecutorMode,
) -> type[BaseModel]:

    if mode == ExecutorMode.ONE:
        return _build_one_mode_model(actions)

    if mode == ExecutorMode.ALL:
        return _build_all_mode_model(actions)

    return _build_many_mode_model(actions)


# =========================================================
# MANY
# =========================================================


def _build_many_mode_model(
    actions: list[Action],
) -> type[BaseModel]:

    combined_fields = {}

    for action in actions:
        action_name = action.name

        should_execute_field_name = _should_execute_field_name(
            action_name
        )

        arguments_field_name = _arguments_field_name(
            action_name,
            action.multi,
        )

        arguments_field = _build_arguments_field(
            action_name=action_name,
            action_model=action.model,
            multi=action.multi,
            required=False,
        )

        action_sub_model = create_model(
            f"{action_name}_action_execution_request",

            __base__=_build_many_action_validation_model(
                should_execute_field_name=should_execute_field_name,
                arguments_field_name=arguments_field_name,
                multi=action.multi,
            ),

            **{
                should_execute_field_name: (
                    bool,
                    Field(
                        description=(
                            f"Set to true only if the "
                            f"'{action_name}' action "
                            f"should actually be executed."
                        ),
                    ),
                ),

                arguments_field_name: arguments_field,
            }
        )

        combined_fields[
            f"{action_name}_action_request"
        ] = (
            action_sub_model,
            Field(
                description=(
                    f"Execution request definition "
                    f"for action '{action_name}'."
                ),
            ),
        )

    return create_model(
        "multiple_action_execution_requests",

        **combined_fields,
    )


# =========================================================
# ALL
# =========================================================


def _build_all_mode_model(
    actions: list[Action],
) -> type[BaseModel]:

    combined_fields = {}

    for action in actions:
        action_name = action.name

        should_execute_field_name = _should_execute_field_name(
            action_name
        )

        arguments_field_name = _arguments_field_name(
            action_name,
            action.multi,
        )

        arguments_field = _build_arguments_field(
            action_name=action_name,
            action_model=action.model,
            multi=action.multi,
            required=True,
        )

        action_sub_model = create_model(
            f"{action_name}_required_action_execution",

            **{
                should_execute_field_name: (
                    Literal[True],
                    Field(
                        description=(
                            f"This field is always true because "
                            f"action '{action_name}' must be executed."
                        ),
                    ),
                ),

                arguments_field_name: arguments_field,
            }
        )

        combined_fields[
            f"{action_name}_required_action_request"
        ] = (
            action_sub_model,
            Field(
                description=(
                    f"Required execution request "
                    f"for action '{action_name}'."
                ),
            ),
        )

    return create_model(
        "required_action_execution_requests",

        **combined_fields,
    )


# =========================================================
# ONE
# =========================================================


def _build_one_mode_model(
    actions: list[Action],
) -> type[BaseModel]:

    union_models = []

    for action in actions:
        action_name = action.name

        arguments_field_name = _arguments_field_name(
            action_name,
            action.multi,
        )

        arguments_field = _build_arguments_field(
            action_name=action_name,
            action_model=action.model,
            multi=action.multi,
            required=True,
            selected=True,
        )

        action_model = create_model(
            f"{action_name}_selected_action_execution",

            **{
                "selected_action_name_for_execution": (
                    Literal[action_name],
                    Field(
                        description=(
                            f"Indicates that action "
                            f"'{action_name}' was selected "
                            f"for execution."
                        ),
                    ),
                ),

                arguments_field_name: arguments_field,
            }
        )

        union_models.append(action_model)

    union_type = union_models[0]

    for model in union_models[1:]:
        union_type = union_type | model

    return create_model(
        "single_action_execution_request",

        selected_action_for_execution=(
            union_type,
            Field(
                description=(
                    "Definition of the single action "
                    "that should be executed."
                ),
            ),
        ),
    )


# =========================================================
# HELPERS
# =========================================================


def _should_execute_field_name(
    action_name: str,
) -> str:

    return (
        f"{action_name}_action_should_be_executed"
    )


def _arguments_field_name(
    action_name: str,
    multi: bool,
) -> str:

    if multi:
        return (
            f"{action_name}_action_calls_to_execute"
        )

    return (
        f"{action_name}_action_arguments"
    )


def _build_arguments_field(
    action_name: str,
    action_model: type[BaseModel],
    multi: bool,
    required: bool,
    selected: bool = False,
):

    if multi:
        description = (
            f"List of calls to execute "
            f"for action '{action_name}'."
        )

        if selected:
            description = (
                f"List of calls to execute "
                f"for selected action '{action_name}'."
            )

        if required:
            return (
                list[action_model],
                Field(
                    min_length=1,
                    description=description,
                ),
            )

        return (
            list[action_model],
            Field(
                default_factory=list,
                description=description,
            ),
        )

    description = (
        f"Arguments required for executing "
        f"action '{action_name}'."
    )

    if selected:
        description = (
            f"Arguments required for executing "
            f"selected action '{action_name}'."
        )

    if required:
        return (
            action_model,
            Field(
                description=description,
            ),
        )

    return (
        action_model | None,
        Field(
            default=None,
            description=(
                f"{description} "
                f"Leave as null if the action "
                f"should not be executed."
            ),
        ),
    )


def _build_many_action_validation_model(
    should_execute_field_name: str,
    arguments_field_name: str,
    multi: bool,
):

    class ManyActionValidationModel(BaseModel):

        @model_validator(mode="after")
        def validate_execution_consistency(self):

            should_execute = getattr(
                self,
                should_execute_field_name,
            )

            arguments = getattr(
                self,
                arguments_field_name,
            )

            if should_execute:
                if multi:
                    if not arguments:
                        raise ValueError(
                            f"Action marked for execution "
                            f"must contain at least one call."
                        )

                else:
                    if arguments is None:
                        raise ValueError(
                            f"Action marked for execution "
                            f"must contain arguments."
                        )

            else:
                if multi:
                    if arguments:
                        raise ValueError(
                            f"Action not marked for execution "
                            f"cannot contain calls."
                        )

                else:
                    if arguments is not None:
                        raise ValueError(
                            f"Action not marked for execution "
                            f"cannot contain arguments."
                        )

            return self

    return ManyActionValidationModel