# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
# odyss_ai_flows/core/run_context.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional
from contextvars import ContextVar
import uuid


@dataclass
class TopRunState:
    run_id: str                 # globally unique for this top run
    top_run_name: str           # explicit name or short uuid
    scope_counters: Dict[str, int] = field(default_factory=dict)


RUN_STATE: ContextVar[Optional[TopRunState]
                      ] = ContextVar("RUN_STATE", default=None)
RUN_NAME:  ContextVar[Optional[str]] = ContextVar("RUN_NAME",  default=None)


def _short_uuid8() -> str:
    return uuid.uuid4().hex[:8]


def ensure_top_run_state(explicit_top_name: Optional[str] = None) -> TopRunState:
    """
    Create (or return existing) TopRunState. If creating new, use explicit_top_name
    or an auto short uuid8 for the top run name.
    """
    state = RUN_STATE.get()
    if state is None:
        top_name = explicit_top_name if explicit_top_name else _short_uuid8()
        state = TopRunState(run_id=str(uuid.uuid4()), top_run_name=top_name)
        RUN_STATE.set(state)
    else:
        # If caller provided an explicit name later, keep existing (first wins).
        pass
    return state


def next_index_for_scope(scope: str) -> int:
    state = RUN_STATE.get()
    if state is None:
        # If somehow called outside a top run, initialize implicit state.
        state = ensure_top_run_state()
    idx = state.scope_counters.get(scope, 0)
    state.scope_counters[scope] = idx + 1
    return idx


def set_run_name(name: Optional[str]):
    return RUN_NAME.set(name)


def get_run_name() -> Optional[str]:
    return RUN_NAME.get()


def current_top_run_name() -> Optional[str]:
    s = RUN_STATE.get()
    return s.top_run_name if s else None


def current_top_run_id() -> Optional[str]:
    s = RUN_STATE.get()
    return s.run_id if s else None
