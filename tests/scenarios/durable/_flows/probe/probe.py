from odyss_ai_flows import iget, node


@node
async def probe():
    # Reports which inputs reached this flow, so a caller can observe propagation
    # (output_keys threading, subflow group-output) from the outside. iget is synchronous.
    return {
        "message_in": iget("message", "ABSENT"),
        "echo_in": iget("echo", "ABSENT"),
        "shared_in": iget("shared", "ABSENT"),
    }
