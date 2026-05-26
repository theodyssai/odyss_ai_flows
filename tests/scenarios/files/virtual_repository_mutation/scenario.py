from __future__ import annotations

from pathlib import Path

from odyss_ai_flows.core.files.api import (
    init_file_repo,
    fget,
)

from odyss_ai_flows.core.files.api import (
    _CURRENT_REPO,
)


async def run_scenario():

    # -------------------------------------------------
    # Init repository
    # -------------------------------------------------

    init_file_repo(
        flow_path=Path("flow"),
    )

    repo = _CURRENT_REPO.get()

    # =================================================
    # ADDITIVE PYTHON NODE
    # =================================================

    def dynamic_node():
        return "dynamic"

    repo.fset(
        "flow/dynamic.py",
        dynamic_node,
    )

    dynamic = fget(
        "node:python",
        name="dynamic",
    )

    assert dynamic is not None

    assert dynamic.kind == "node:python"

    assert (
        dynamic.rebased_path
        == Path("flow/dynamic.py")
    )

    assert (
        dynamic.callable_obj
        is dynamic_node
    )

    # =================================================
    # ADDITIVE JINJA NODE
    # =================================================

    repo.fset(
        "flow/template.jinja2",
        "Hello {{ name }}",
    )

    template = fget(
        "node:jinja",
        name="template",
    )

    assert template is not None

    assert (
        template.content
        == "Hello {{ name }}"
    )

    assert (
        template.callable_obj
        is None
    )

    # =================================================
    # REDIRECTED PATH ENTRY
    # =================================================

    repo.fset(
        "flow/link.py",
        Path("external/source.py"),
    )

    linked = fget(
        "node:python",
        name="link",
    )

    assert linked is not None

    assert (
        linked.redirected_path
        == Path("external/source.py")
    )

    # =================================================
    # OVERRIDE EXISTING NODE
    # =================================================

    def replacement_hello():
        return "replacement"

    repo.fset(
        "flow/hello.py",
        replacement_hello,
    )

    hello = fget(
        "node:python",
        name="hello",
    )

    assert hello is not None

    assert hello.source == "fset"

    assert (
        hello.callable_obj
        is replacement_hello
    )

    # =================================================
    # INDEX CONSISTENCY
    # =================================================

    all_python = fget(
        "node:python"
    )

    names = {
        entry.name
        for entry in all_python
    }

    assert names == {
        "hello",
        "dynamic",
        "link",
    }