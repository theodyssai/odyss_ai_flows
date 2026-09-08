from __future__ import annotations

from typing import Callable

from tests.tests_runtime.requirements.base import (
    CONFIG_AXIS,
    DEFAULT_LLM_ENV_VARS,
    DEFAULT_LLM_PLUGIN_DIST,
    DEFAULT_LLM_PLUGIN_ENTRY_POINT,
    CheckFn,
    Requirement,
)

from tests.tests_runtime.requirements.types import (
    AnyProviderRequirement,
    CommandRequirement,
    CustomRequirement,
    EnvRequirement,
    PluginRequirement,
)


# ---------------------------------------------------------
# Factories
# ---------------------------------------------------------

def plugin(
    dist: str,
    *,
    entry_point: str | None = None,
    group: str | None = None,
) -> PluginRequirement:
    """Require a specific installed plugin distribution (hard)."""

    return PluginRequirement(
        dist=dist,
        entry_point=entry_point,
        group=group,
    )


def any_provider() -> AnyProviderRequirement:
    """Require any LLM provider plugin (discouraged — prefer plugin())."""

    return AnyProviderRequirement()


def env(
    *vars: str,
    consult_env_local: bool = True,
) -> EnvRequirement:
    """Require environment variables (soft); also reads .env.local."""

    return EnvRequirement(
        vars=tuple(vars),
        consult_env_local=consult_env_local,
    )


def command(
    *argv: str,
    expect_exit: int = 0,
    timeout: float = 10.0,
) -> CommandRequirement:
    """Require a probe command to run and exit as expected (soft)."""

    return CommandRequirement(
        argv=tuple(argv),
        expect_exit=expect_exit,
        timeout=timeout,
    )


def custom(
    check_fn: CheckFn,
    description: str,
    *,
    axis: str = CONFIG_AXIS,
    cache_key: str | None = None,
) -> CustomRequirement:
    """Wrap a check function inline.

    The function receives the scenario directory (or takes no argument)
    and returns a bool, a ``(bool, detail)`` pair, or a RequirementStatus.
    """

    return CustomRequirement(
        check_fn=check_fn,
        description=description,
        axis=axis,
        cache_key=cache_key,
    )


def custom_check(
    description: str,
    *,
    axis: str = CONFIG_AXIS,
    cache_key: str | None = None,
) -> Callable[[CheckFn], CustomRequirement]:
    """Decorator form of :func:`custom`.

        @custom_check("docker daemon reachable")
        def docker_up(scenario_dir):
            return _ping_docker()

        REQUIREMENTS = [docker_up]
    """

    def decorate(check_fn: CheckFn) -> CustomRequirement:
        return CustomRequirement(
            check_fn=check_fn,
            description=description,
            axis=axis,
            cache_key=cache_key,
        )

    return decorate


# ---------------------------------------------------------
# Presets
# ---------------------------------------------------------

def provider(
    dist: str,
    *env_vars: str,
    entry_point: str | None = None,
    group: str | None = None,
    consult_env_local: bool = True,
) -> list[Requirement]:
    """A provider-plugin bundle: the plugin + the env vars it needs.

    The generic form of :func:`azure`, so a *new* plugin needs no runtime
    changes to get a one-line requirement — just declare it in the
    scenario's ``requirements.py``::

        REQUIREMENTS = requires().provider(
            "odyss_ai_flows_foo", "FOO_API_KEY", "FOO_ENDPOINT",
            entry_point="call_foo",
        )
    """

    reqs: list[Requirement] = [
        PluginRequirement(
            dist=dist,
            entry_point=entry_point,
            group=group,
        )
    ]

    if env_vars:
        reqs.append(
            EnvRequirement(
                vars=tuple(env_vars),
                consult_env_local=consult_env_local,
            )
        )

    return reqs


def azure() -> list[Requirement]:
    """The standard Azure OpenAI bundle: the plugin + its env vars."""

    return provider(
        DEFAULT_LLM_PLUGIN_DIST,
        *DEFAULT_LLM_ENV_VARS,
        entry_point=DEFAULT_LLM_PLUGIN_ENTRY_POINT,
    )


# ---------------------------------------------------------
# Fluent builder
# ---------------------------------------------------------

class Requires(list):
    """Chainable builder for a scenario's requirements.

    Returned by :func:`requires`. Every method appends a requirement and
    returns ``self``, and the builder *is* the list, so a scenario writes::

        REQUIREMENTS = (
            requires()
            .plugin("odyss_ai_flows_azure", entry_point="call_azure")
            .env("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")
        )
    """

    def add(self, *requirements: Requirement) -> "Requires":
        """Append already-built Requirement(s) — escape hatch for
        custom Requirement subclasses."""

        for req in requirements:

            if not isinstance(req, Requirement):
                raise TypeError(
                    f"requires().add() expects Requirement instances, "
                    f"got {type(req).__name__}"
                )

            self.append(req)

        return self

    def plugin(
        self,
        dist: str,
        *,
        entry_point: str | None = None,
        group: str | None = None,
    ) -> "Requires":
        return self.add(
            plugin(
                dist,
                entry_point=entry_point,
                group=group,
            )
        )

    def any_provider(self) -> "Requires":
        return self.add(any_provider())

    def env(
        self,
        *vars: str,
        consult_env_local: bool = True,
    ) -> "Requires":
        return self.add(
            env(
                *vars,
                consult_env_local=consult_env_local,
            )
        )

    def command(
        self,
        *argv: str,
        expect_exit: int = 0,
        timeout: float = 10.0,
    ) -> "Requires":
        return self.add(
            command(
                *argv,
                expect_exit=expect_exit,
                timeout=timeout,
            )
        )

    def check(
        self,
        description: str,
        check_fn: CheckFn,
        *,
        axis: str = CONFIG_AXIS,
        cache_key: str | None = None,
    ) -> "Requires":
        """Inline custom check. ``check_fn`` returns bool /
        ``(bool, detail)`` / RequirementStatus."""

        return self.add(
            custom(
                check_fn,
                description,
                axis=axis,
                cache_key=cache_key,
            )
        )

    def provider(
        self,
        dist: str,
        *env_vars: str,
        entry_point: str | None = None,
        group: str | None = None,
        consult_env_local: bool = True,
    ) -> "Requires":
        return self.add(
            *provider(
                dist,
                *env_vars,
                entry_point=entry_point,
                group=group,
                consult_env_local=consult_env_local,
            )
        )

    def azure(self) -> "Requires":
        return self.add(*azure())


def requires() -> Requires:
    """Start a fluent requirement chain (see :class:`Requires`)."""

    return Requires()
