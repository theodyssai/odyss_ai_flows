# Setup:
#   pip install -e plugins/odyss_ai_flows_token_limiter[test]
#   pip install -e plugins/odyss_ai_flows_azure
#   Copy .env.local.example -> .env.local and fill in the four Azure vars,
#   or export them directly: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION,
#   AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_KEY
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
    .azure()
)
