def get_pipelines():
    return {

        # -----------------------------------------------------
        # Default adaptive OpenRouter pipeline
        # -----------------------------------------------------

        "openrouter_default": [
            "render",
            "messages_role",

            # Opportunistic action augmentation
            "action_model",

            # Adaptive caller:
            # - text mode if no model_class
            # - structured mode otherwise
            "call_openrouter",

            "finish_reason_logger",
            "token_counter",

            # Opportunistic action execution
            "action_execute",
        ],

        # -----------------------------------------------------
        # Streaming pipeline
        # -----------------------------------------------------

        "openrouter_streaming": [
            "render",
            "messages_role",

            "call_openrouter_streaming",

            "finish_reason_logger",
            "token_counter",
        ],
    }
