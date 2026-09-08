# Setup: pip install -e plugins/odyss_ai_flows_token_limiter[test]
# (the [test] extra pulls in fakeredis; no credentials or live services needed)
from tests.tests_runtime.requirements import PLUGIN_AXIS, requires


def _fakeredis_importable():
    try:
        import fakeredis  # noqa: F401
        return True
    except ImportError:
        return (False, 'install with: pip install -e "plugins/odyss_ai_flows_token_limiter[test]"')


REQUIREMENTS = (
    requires()
    .plugin("odyss_ai_flows_token_limiter")
    .check("fakeredis importable", _fakeredis_importable, axis=PLUGIN_AXIS)
)
