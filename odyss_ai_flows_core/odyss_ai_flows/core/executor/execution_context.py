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

_current_executor = ContextVar(
    "current_executor", default=None)


def set_executor(executor):
    return _current_executor.set(executor)


def reset_executor(token):
    _current_executor.reset(token)


def get_executor():
    return _current_executor.get()
