# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


@dataclass
class FileMatcher:
    kind: str
    match: Callable[[Path], bool]
    extract_name: Optional[Callable[[Path], str]] = None


def default_matchers():
    return [
        FileMatcher(
            kind="node:jinja",
            match=lambda p: p.suffix == ".jinja2",
            extract_name=lambda p: p.stem
        ),
        FileMatcher(
            kind="node:model",
            match=lambda p: p.suffixes == [".model", ".py"],
            extract_name=lambda p: p.name.removesuffix(".model.py")
        ),
        FileMatcher(
            kind="config:folder",
            match=lambda p: p.name == "config.json"
        ),
        FileMatcher(
            kind="config:node",
            match=lambda p: p.name.endswith(".config.json"),
            extract_name=lambda p: p.name.removesuffix(".config.json")
        ),
        FileMatcher(
            kind="node:python",
            match=lambda p: (
                p.suffix == ".py"
                and p.name != "__init__.py"
                and not p.name.endswith(".model.py")
            ),
            extract_name=lambda p: p.stem
        ),
        FileMatcher(
            kind="flow:outputs",
            match=lambda p: p.name == "outputs.json"
        )
    ]


_registered_matchers: list[FileMatcher] = default_matchers()


def register_matcher(matcher: FileMatcher):
    _registered_matchers.append(matcher)


def get_registered_matchers() -> list[FileMatcher]:
    return list(_registered_matchers)
