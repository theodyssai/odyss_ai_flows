from odyss_ai_flows import nget, node


@node
async def consumer():
    # Core accepts a variable here, but the durable static DAG scan sees only
    # string-literal nget arguments and therefore does not prelaunch producer.
    dependency = "producer"
    return f"consumer saw {await nget(dependency)}"
