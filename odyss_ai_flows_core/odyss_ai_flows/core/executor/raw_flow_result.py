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
from enum import Enum
from typing import Any, Optional
from pathlib import Path


class FlowStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    BREAK = "break"


@dataclass
class RawFlowResult:
    status: FlowStatus
    results: dict[str, Any]
    path_to_node_map: dict[Path, list[str]]
    callable_to_node_map: dict[int, list[str]]
    error: Optional[BaseException] = None
    suppressed_error: Optional[BaseException] = None