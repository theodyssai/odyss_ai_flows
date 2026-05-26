# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
import json
from pathlib import Path
from typing import Any


class SensitiveValue(str):

    PLACEHOLDER = "<SensitiveValue>"

    def __new__(
        cls,
        value: Any,
    ):

        obj = super().__new__(
            cls,
            cls.PLACEHOLDER,
        )

        obj.__real_value = value

        return obj

    # ---------------------------------------------------------
    # Explicit access
    # ---------------------------------------------------------

    def unwrap(self) -> Any:
        return self.__real_value

    # ---------------------------------------------------------
    # Display semantics
    # ---------------------------------------------------------

    def __str__(self) -> str:
        return self.PLACEHOLDER

    def __repr__(self) -> str:
        return self.PLACEHOLDER


def deep_merge_dicts(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge_dicts(result[k], v)
        else:
            result[k] = v
    return result


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
