# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
import contextvars
from typing import Any, Dict, Union, Sequence

from odyss_ai_flows.core.config.utils import SensitiveValue
from odyss_ai_flows.core.config.api import cget


_CURRENT_INPUTS = contextvars.ContextVar("CURRENT_INPUTS")
_INJECTED_NODE_RESULTS: contextvars.ContextVar[
    Dict[str, Any] | None
] = contextvars.ContextVar("INJECTED_NODE_RESULTS", default=None)


def set_inputs(values: Dict[str, Any]):
    _CURRENT_INPUTS.set(values)


def iget(
    keys: Union[str, Sequence[str]],
    default: Union[Any, Sequence[Any]] = None
) -> Union[Any, tuple[Any, ...]]:
    repo = _CURRENT_INPUTS.get(None)
    if repo is None:
        raise RuntimeError("iget() used without active input context.")

    is_single = isinstance(keys, str)
    keys_list = [keys] if is_single else list(keys)

    # Only treat default as per-key if keys is a list and default is a list/tuple
    if not is_single and isinstance(default, Sequence) and not isinstance(default, str):
        if len(default) != len(keys_list):
            raise ValueError("Length of defaults must match length of keys")
        defaults = list(default)
    else:
        defaults = [default] * len(keys_list)

    results = [repo.get(k, d) for k, d in zip(keys_list, defaults)]
    return results[0] if is_single else tuple(results)



def set_injected_results(results: Dict[str, Any] | None) -> None:
    _INJECTED_NODE_RESULTS.set(results)


def get_injected_results() -> Dict[str, Any] | None:
    return _INJECTED_NODE_RESULTS.get()


async def wrap_sensitive_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    sensitive_keys = await cget("inputs.sensitive_keys", default=[])
    return {
        k: SensitiveValue(v) if k in sensitive_keys else v
        for k, v in inputs.items()
    }





