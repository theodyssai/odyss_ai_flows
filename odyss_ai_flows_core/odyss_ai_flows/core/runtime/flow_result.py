# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
# odyss_ai_flows/core/runtime/flow_result.py

import json

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Union

from odyss_ai_flows.core.executor.raw_flow_result import (
    RawFlowResult,
)

from odyss_ai_flows.core.files.api import (
    fget,
)

from odyss_ai_flows.core.config.utils import (
    SensitiveValue,
)


def unwrap(value):
    if isinstance(value, SensitiveValue):
        return value.unwrap()
    return value


class FlowResult:
    def __init__(
        self,
        raw: RawFlowResult,
    ):
        self._raw = raw

        (
            self._final_results,
            self._exported_raw_names,
        ) = _extract_outputs_metadata(
            raw.results
        )

    # ---------------------------------------------------------
    # Canonical output view (single chokepoint)
    # ---------------------------------------------------------

    def _output_view(self) -> dict[str, Any]:
        return self._final_results

    # ---------------------------------------------------------
    # Core properties
    # ---------------------------------------------------------

    @property
    def status(self):
        return self._raw.status

    @property
    def error(self):
        return self._raw.error

    @property
    def suppressed_error(self):
        return self._raw.suppressed_error

    @property
    def all_node_results(
        self,
    ) -> dict[str, Any]:

        return self._raw.results

    @property
    def outputs(
        self,
    ) -> dict[str, Any]:

        return dict(self._output_view())

    # ---------------------------------------------------------
    # Collection protocol
    # ---------------------------------------------------------

    def __iter__(self):

        return iter(self._output_view())

    def __len__(self) -> int:

        return len(self._output_view())

    def __contains__(self, key) -> bool:

        try:
            self[key]
            return True
        except (KeyError, TypeError, ValueError):
            return False

    def keys(self):

        return self._output_view().keys()

    def values(self):

        return self._output_view().values()

    def items(self):

        return self._output_view().items()

    # ---------------------------------------------------------
    # Result access
    # ---------------------------------------------------------

    def __getitem__(
        self,
        key: Union[
            str,
            Callable[..., Any],
        ],
    ) -> Any:

        # -----------------------------------------------------
        # String access (canonical)
        # -----------------------------------------------------

        if isinstance(key, str):

            name = key

        # -----------------------------------------------------
        # Callable access
        # -----------------------------------------------------

        elif callable(key):

            fn = key



            # -------------------------------------------------
            # FIRST: callable identity resolution
            # -------------------------------------------------

            names = (
                self._raw
                .callable_to_node_map
                .get(id(fn))
            )

            if names:

                if len(names) > 1:

                    raise KeyError(
                        f"Multiple nodes correspond "
                        f"to callable "
                        f"'{fn.__name__}': "
                        f"{names}"
                    )

                name = names[0]

            else:

                # ---------------------------------------------
                # SECOND: path-based fallback
                # ---------------------------------------------

                func_path = getattr(
                    fn,
                    "__flow_node_path__",
                    None,
                )

                if not isinstance(
                    func_path,
                    Path,
                ):
                    raise ValueError(
                        "Missing or invalid "
                        "__flow_node_path__"
                    )

                func_path = (
                    func_path
                    .resolve()
                )

                names = (
                    self._raw
                    .path_to_node_map
                    .get(func_path)
                )

                if not names:

                    raise KeyError(
                        f"No node corresponds "
                        f"to function path: "
                        f"{func_path}"
                    )

                if len(names) > 1:

                    raise KeyError(
                        f"Multiple nodes correspond "
                        f"to function path "
                        f"{func_path}: "
                        f"{names}"
                    )

                name = names[0]

        # -----------------------------------------------------
        # Invalid key type
        # -----------------------------------------------------

        else:

            raise TypeError(
                f"Unsupported key type: "
                f"{type(key)}"
            )

        # -----------------------------------------------------
        # STRING LOOKUP
        # -----------------------------------------------------

        if isinstance(
            key,
            str,
        ):

            if name not in self._final_results:

                raise KeyError(
                    f"Key '{name}' not found "
                    f"in results"
                )

            return self._final_results[
                name
            ]

        # -----------------------------------------------------
        # CALLABLE LOOKUP
        # -----------------------------------------------------

        if (
            name
            not in self._exported_raw_names
        ):

            raise KeyError(
                f"Key '{name}' not found "
                f"in results"
            )

        return self._raw.results[
            name
        ]

    # ---------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:

        return {
            "outputs": (
                self._final_results
            ),

            "status": (
                self.status.value
            ),

            "error": (
                str(self.error)
                if self.error
                else None
            ),
        }

    def to_json(self) -> str:

        return json.dumps(
            _safe_serialize(
                self.to_dict()
            ),
            indent=4,
        )

    def __str__(self):

        return self.to_json()


# ---------------------------------------------------------
# outputs.json handling
# ---------------------------------------------------------

def _extract_outputs_metadata(
    all_results: dict[str, Any],
) -> tuple[
    dict[str, Any],
    set[str],
]:

    entries = fget(
        "flow:outputs"
    )

    # ---------------------------------------------------------
    # No outputs.json
    # ---------------------------------------------------------

    if not entries:

        return (
            all_results.copy(),
            set(all_results.keys()),
        )

    # ---------------------------------------------------------
    # Ambiguous outputs.json
    # ---------------------------------------------------------

    if len(entries) > 1:

        raise RuntimeError(
            "Multiple outputs.json "
            "detected in flow "
            "(ambiguous)"
        )

    entry = entries[0]

    spec = _load_outputs_spec(
        entry
    )

    include = spec.get(
        "include"
    )

    mapping = spec.get(
        "map",
        {},
    )

    sensitive = spec.get(
        "sensitive",
        [],
    )

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    if (
        include is not None
        and not isinstance(
            include,
            list,
        )
    ):
        raise ValueError(
            "'include' must be a list"
        )

    if not isinstance(
        mapping,
        dict,
    ):
        raise ValueError(
            "'map' must be a dict"
        )

    if not isinstance(
        sensitive,
        list,
    ):
        raise ValueError(
            "'sensitive' must be a list"
        )

    sensitive_set = set(
        sensitive
    )

    # ---------------------------------------------------------
    # Determine exported node identities
    # ---------------------------------------------------------

    if include is None:

        exported_raw_names = set(
            all_results.keys()
        )

        keys = all_results.keys()

    else:

        exported_raw_names = set(
            include
        )

        keys = include

    # ---------------------------------------------------------
    # Build projected outputs
    # ---------------------------------------------------------

    result = {}

    for key in keys:

        if key not in all_results:
            continue

        value = all_results[key]

        if key in sensitive_set:
            value = SensitiveValue(value)

        output_key = mapping.get(
            key,
            key,
        )

        result[output_key] = value

    return (
        result,
        exported_raw_names,
    )


def _load_outputs_spec(
    entry,
) -> dict:
    """
    Load outputs.json from FileEntry.
    """

    # ---------------------------------------------------------
    # content
    # ---------------------------------------------------------

    if entry.content is not None:

        try:

            return json.loads(
                entry.content
            )

        except Exception as e:

            raise ValueError(
                f"Failed to parse "
                f"outputs.json "
                f"(content): {e}"
            )

    # ---------------------------------------------------------
    # redirected path
    # ---------------------------------------------------------

    if entry.redirected_path is not None:

        try:

            return json.loads(
                entry.redirected_path
                .read_text()
            )

        except Exception as e:

            raise ValueError(
                f"Failed to parse "
                f"outputs.json "
                f"(redirected): {e}"
            )

    # ---------------------------------------------------------
    # real path
    # ---------------------------------------------------------

    if entry.real_path is not None:

        try:

            return json.loads(
                entry.real_path
                .read_text()
            )

        except Exception as e:

            raise ValueError(
                f"Failed to parse "
                f"outputs.json: {e}"
            )

    # ---------------------------------------------------------
    # callable invalid
    # ---------------------------------------------------------

    if entry.callable_obj is not None:

        raise TypeError(
            "outputs.json does not "
            "support callable values"
        )

    raise RuntimeError(
        "Invalid outputs.json entry"
    )


# ---------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------

def _safe_serialize(
    obj,
):

    if isinstance(
        obj,
        SensitiveValue,
    ):

        return "[REDACTED]"

    if isinstance(
        obj,
        dict,
    ):

        return {
            k: _safe_serialize(v)
            for k, v
            in obj.items()
        }

    elif isinstance(
        obj,
        list,
    ):

        return [
            _safe_serialize(v)
            for v in obj
        ]

    elif isinstance(
        obj,
        tuple,
    ):

        return [
            _safe_serialize(v)
            for v in obj
        ]

    elif isinstance(
        obj,
        SimpleNamespace,
    ):

        return _safe_serialize(
            vars(obj)
        )

    elif hasattr(
        obj,
        "to_dict",
    ):

        return _safe_serialize(
            obj.to_dict()
        )

    elif isinstance(
        obj,
        (
            str,
            int,
            float,
            bool,
            type(None),
        ),
    ):

        return obj

    else:

        return str(obj)