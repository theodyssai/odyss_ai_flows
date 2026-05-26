# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
from pathlib import Path
from typing import Any, Callable, Optional

from odyss_ai_flows.core.files.matcher_registry import get_registered_matchers
from odyss_ai_flows.core.files.repository import FileEntry


def build_file_entry(
    *,
    rebased_path: Path,
    real_path: Optional[Path],
    source: str,
    value: Any = None,
) -> FileEntry:
    matchers = get_registered_matchers()

    # -------------------------
    # Resolve kind + name
    # -------------------------
    for matcher in matchers:
        if matcher.match(rebased_path):
            name = matcher.extract_name(rebased_path) if matcher.extract_name else None
            kind = matcher.kind
            break
    else:
        name = None
        kind = "unknown"

    # -------------------------
    # Resolve content type
    # -------------------------
    content = None
    callable_obj = None
    redirected_path = None

    if value is not None:
        if isinstance(value, str):
            content = value
        elif callable(value):
            callable_obj = value
        elif isinstance(value, Path):
            redirected_path = value
        else:
            raise TypeError(f"Unsupported fset value type: {type(value)}")
        
    # ---------------------------------------------------------
# Normalize semantic config scopes
# ---------------------------------------------------------

    if kind == "config:folder":

        rebased_path = rebased_path.parent

    elif kind == "config:node":

        assert name is not None

        rebased_path = (
            rebased_path.parent
            / name
        )

    return FileEntry(
        real_path=real_path,
        rebased_path=rebased_path,
        kind=kind,
        name=name,
        source=source,
        content=content,
        callable_obj=callable_obj,
        redirected_path=redirected_path,
    )