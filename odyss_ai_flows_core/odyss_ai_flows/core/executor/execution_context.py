# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
from contextvars import ContextVar
from typing import Optional

_current_executor = ContextVar(
    "current_executor", default=None)

_current_node_name: ContextVar[Optional[str]] = ContextVar(
    "current_node_name", default=None)


def set_executor(executor):
    return _current_executor.set(executor)


def reset_executor(token):
    _current_executor.reset(token)


def get_executor():
    return _current_executor.get()


def set_current_node_name(name: Optional[str]):
    return _current_node_name.set(name)


def reset_current_node_name(token):
    _current_node_name.reset(token)


def get_current_node_name() -> Optional[str]:
    return _current_node_name.get()
