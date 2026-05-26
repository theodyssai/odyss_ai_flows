from odyss_ai_flows import *


@node
async def runtime_node():

    return {

        "plain_string": await cget(
            "plain_string"
        ),

        "jinja_math": await cget(
            "jinja_math"
        ),

        "env_mode": await cget(
            "env_mode"
        ),

        "config_url": await cget(
            "config_url"
        ),

        "async_sum": await cget(
            "async_sum"
        ),

        "ref_nested": await cget(
            "ref_nested"
        ),

        "dict_recursive": await cget(
            "dict_recursive"
        ),

        "list_recursive": await cget(
            "list_recursive"
        ),

        "secret_value": await cget(
            "secret_value"
        ),

        "mixed_secret": await cget(
            "mixed_secret"
        ),

        "variant_value": await cget(
            "variant_value"
        ),
    }