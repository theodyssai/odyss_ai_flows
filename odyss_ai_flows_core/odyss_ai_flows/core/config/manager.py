# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
# core/config/manager.py

from typing import Any, Optional
from copy import deepcopy
from pathlib import Path

from odyss_ai_flows.core.config.tree import ConfigNode
from odyss_ai_flows.core.config.resolver import resolve
from odyss_ai_flows.core.config.providers import ConfigReference


class ConfigManager:

    def __init__(self, root: ConfigNode):
        self.root = root

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    async def get(
        self,
        key: str,
        *,
        default: Optional[Any] = None,
        node_scope: Optional[str] = "",
    ) -> Any:

        key_path = key.split(".")
        scope_parts = Path(node_scope).parts if node_scope else []

        value_found = False
        current_value = None
        treating_as_dict = False

        # ---------------------------------------------------------
        # Scope traversal
        # ---------------------------------------------------------

        def traverse_and_check(node: ConfigNode):

            nonlocal value_found
            nonlocal current_value
            nonlocal treating_as_dict

            sub_config = node.config

            for part in key_path:

                if not isinstance(sub_config, dict):
                    return

                if part not in sub_config:
                    return

                sub_config = sub_config[part]

            # ---------------------------------------------------------
            # Dict merge semantics
            # ---------------------------------------------------------

            if isinstance(sub_config, dict):

                if not value_found or not treating_as_dict:

                    current_value = deepcopy(sub_config)
                    treating_as_dict = True

                else:

                    current_value = self._deep_merge_dicts(
                        current_value,
                        sub_config,
                    )

                value_found = True

            # ---------------------------------------------------------
            # Scalar overwrite semantics
            # ---------------------------------------------------------

            else:

                current_value = sub_config
                treating_as_dict = False
                value_found = True

        # ---------------------------------------------------------
        # Root config
        # ---------------------------------------------------------

        node = self.root

        traverse_and_check(node)

        # ---------------------------------------------------------
        # Scoped overrides
        # ---------------------------------------------------------

        for part in scope_parts:

            if part in node.children:

                node = node.children[part]

                traverse_and_check(node)

            else:
                break

        val = current_value if value_found else default

        # ---------------------------------------------------------
        # Semantic resolution
        # ---------------------------------------------------------

        val = await resolve(
            val        )

        # ---------------------------------------------------------
        # REF traversal
        # ---------------------------------------------------------

        val = await self._resolve_references(
            val,
            node_scope=node_scope,
        )

        return val

    # ---------------------------------------------------------
    # REF traversal
    # ---------------------------------------------------------

    async def _resolve_references(
        self,
        val: Any,
        *,
        node_scope: Optional[str],
    ) -> Any:

        # ---------------------------------------------------------
        # Direct REF
        # ---------------------------------------------------------

        if isinstance(val, ConfigReference):

            return await self.get(
                val.path,
                node_scope=node_scope,
            )

        # ---------------------------------------------------------
        # List recursion
        # ---------------------------------------------------------

        if isinstance(val, list):

            return [
                await self._resolve_references(
                    item,
                    node_scope=node_scope,
                )
                for item in val
            ]

        # ---------------------------------------------------------
        # Dict recursion
        # ---------------------------------------------------------

        if isinstance(val, dict):

            return {
                k: await self._resolve_references(
                    v,
                    node_scope=node_scope,
                )
                for k, v in val.items()
            }

        # ---------------------------------------------------------
        # Primitive passthrough
        # ---------------------------------------------------------

        return val

    # ---------------------------------------------------------
    # Runtime overrides
    # ---------------------------------------------------------

    def override(
        self,
        scope: str,
        key: str,
        value: Any,
    ):

        node = self._ensure_scope(scope)

        target = node.config

        parts = key.split(".")

        for part in parts[:-1]:

            if (
                part not in target
                or not isinstance(target[part], dict)
            ):
                target[part] = {}

            target = target[part]

        target[parts[-1]] = value

    # ---------------------------------------------------------
    # Scope creation
    # ---------------------------------------------------------

    def _ensure_scope(
        self,
        scope: str,
    ) -> ConfigNode:

        if not scope:
            return self.root

        parts = scope.strip("/").split("/")

        node = self.root

        current_path = node.path

        for part in parts:

            current_path = current_path / part

            node = node.ensure_child(
                part,
                current_path,
            )

        return node

    # ---------------------------------------------------------
    # Deep merge
    # ---------------------------------------------------------

    @staticmethod
    def _deep_merge_dicts(
        a: dict,
        b: dict,
    ) -> dict:

        result = deepcopy(a)

        for k, v in b.items():

            if (
                k in result
                and isinstance(result[k], dict)
                and isinstance(v, dict)
            ):

                result[k] = ConfigManager._deep_merge_dicts(
                    result[k],
                    v,
                )

            else:

                result[k] = deepcopy(v)

        return result