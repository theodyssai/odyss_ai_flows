# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
def get_pipelines():
    return {

        # -----------------------------------------------------
        # Default adaptive Azure pipeline
        # -----------------------------------------------------

        "azure_default": [
            "render",
            "messages_role",

            # Opportunistic action augmentation
            "action_model",

            # Adaptive caller:
            # - text mode if no model_class
            # - structured mode otherwise
            "call_azure",

            "finish_reason_logger",
            "token_counter",

            # Opportunistic action execution
            "action_execute",
        ],

        # -----------------------------------------------------
        # Streaming pipeline
        # -----------------------------------------------------

        "azure_streaming": [
            "render",
            "messages_role",

            "call_azure_streaming",

            "finish_reason_logger",
            "token_counter",
        ],
    }