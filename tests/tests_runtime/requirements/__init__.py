"""Scenario prerequisites — what a scenario needs before it can run.

A scenario declares this in a sibling ``requirements.py`` by building a
``REQUIREMENTS`` list with the chainable ``requires()`` builder::

    from tests.tests_runtime.requirements import requires

    REQUIREMENTS = requires().azure()

See the "Test modes & scenario requirements" section of CLAUDE.md for the
full authoring surface, the two axes, and how each mode treats them.

Layout: ``base`` (axes, contract), ``types`` (concrete Requirements),
``builder`` (factories, presets, the fluent builder), ``loading``
(harness-facing normalisation).
"""

from tests.tests_runtime.requirements.base import (
    CONFIG_AXIS,
    PLUGIN_AXIS,
    Requirement,
    RequirementStatus,
)

from tests.tests_runtime.requirements.types import (
    AnyProviderRequirement,
    CommandRequirement,
    CustomRequirement,
    EnvRequirement,
    PluginRequirement,
)

from tests.tests_runtime.requirements.builder import (
    Requires,
    any_provider,
    azure,
    command,
    custom,
    custom_check,
    env,
    plugin,
    provider,
    requires,
)

from tests.tests_runtime.requirements.loading import (
    coerce_requirements,
    default_llm_requirements,
)


__all__ = [
    # preferred authoring surface
    "requires",
    "Requires",
    # axes
    "PLUGIN_AXIS",
    "CONFIG_AXIS",
    # contract
    "Requirement",
    "RequirementStatus",
    # factories (used standalone or behind the builder)
    "plugin",
    "any_provider",
    "env",
    "command",
    "custom",
    "custom_check",
    "provider",
    "azure",
    # classes (for advanced use / isinstance checks)
    "PluginRequirement",
    "AnyProviderRequirement",
    "EnvRequirement",
    "CommandRequirement",
    "CustomRequirement",
    # harness internals
    "coerce_requirements",
    "default_llm_requirements",
]
