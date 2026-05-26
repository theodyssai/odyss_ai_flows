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
from typing import Dict, Optional, Union

from odyss_ai_flows.core.utils.logger import logger


class ConfigNode:
    def __init__(self, name: str, path: Path, parent: Optional["ConfigNode"] = None):
        self.name = name
        self.path = path
        self.parent = parent
        self.children: Dict[str, ConfigNode] = {}
        self.config: dict = {}

    @property
    def path_str(self) -> str:
        parts = []
        node = self
        while node.parent is not None:
            parts.append(node.name)
            node = node.parent
        return "/".join(reversed(parts))

    def ensure_child(self, name: str, path: Path) -> "ConfigNode":
        if name not in self.children:
            self.children[name] = ConfigNode(name, path, parent=self)
        return self.children[name]

    def get_child_by_path(self, path: Union[str, Path]) -> Optional["ConfigNode"]:
        if isinstance(path, Path):
            parts = path.parts
        else:
            parts = path.strip("/").split("/")

        node = self
        for part in parts:
            node = node.children.get(part)
            if node is None:
                return None
        return node

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": str(self.path),
            "config": self.config,
            "children": {k: v.to_dict() for k, v in self.children.items()},
        }

    def pretty_print(self, indent: int = 0, show_config: bool = True, max_depth: Optional[int] = None):
        pad = "  " * indent
        logger.info("%s- %s (Config: %s)", pad,
                    self.path_str or "/", "yes" if self.config else "no")

        if show_config and self.config:
            for k, v in self.config.items():
                short_val = json.dumps(v, ensure_ascii=False) if not isinstance(
                    v, (dict, list)) else "<complex>"
                logger.info("%s    %s: %s", pad, k, short_val)

        if max_depth is not None and indent >= max_depth:
            return

        for child in sorted(self.children.values(), key=lambda c: c.name):
            child.pretty_print(
                indent + 1, show_config=show_config, max_depth=max_depth)

    @staticmethod
    def from_dict(data: dict, parent: Optional["ConfigNode"] = None) -> "ConfigNode":
        node = ConfigNode(data["name"], Path(data["path"]), parent)
        node.config = data["config"]
        for k, v in data["children"].items():
            node.children[k] = ConfigNode.from_dict(v, parent=node)
        return node
