# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
# builder.py

from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import List, Dict, Any

from odyss_ai_flows.core.config.utils import (
    deep_merge_dicts,
    load_json,
)
from odyss_ai_flows.core.files.api import fget
from odyss_ai_flows.core.config.tree import ConfigNode
from odyss_ai_flows.core.config.global_config import (
    get_raw_global_config,
)
from odyss_ai_flows.core.utils.logger import logger
from odyss_ai_flows.core.files.repository import FileEntry


# ---------------------------------------------------------
# Public builder
# ---------------------------------------------------------

async def build_config_tree() -> ConfigNode:
    """
    Build config tree from repository entries.

    Structure is derived entirely from rebased_path (virtual paths).
    """

    root = ConfigNode(
        name="",
        path=Path(),
    )

    # ---------------------------------------------------------
    # Raw global config
    # ---------------------------------------------------------

    root.config = deepcopy(
        get_raw_global_config()
    )

    logger.debug(
        "Building config tree from repository (virtual paths)"
    )

    folder_entries = fget("config:folder")
    node_entries = fget("config:node")

    folder_groups = _group_and_sort_entries(folder_entries)
    node_groups = _group_and_sort_entries(node_entries)

    # ---------------------------------------------------------
    # Folder-level config
    # ---------------------------------------------------------

    for rebased_path, entries in folder_groups.items():

        merged = _merge_ordered_entries(entries)

        _insert_into_tree(
            root,
            rebased_path,
            merged,
        )

    # ---------------------------------------------------------
    # Node-level config
    # ---------------------------------------------------------

    for rebased_path, entries in node_groups.items():

        assert all(
            e.name is not None
            for e in entries
        )

        merged = _merge_ordered_entries(entries)

        _insert_into_tree(
            root,
            rebased_path,
            merged,
        )

    logger.info("Final configuration tree:")

    root.pretty_print()

    return root


# ---------------------------------------------------------
# Grouping + sorting
# ---------------------------------------------------------

def _group_and_sort_entries(
    entries: List[Any],
) -> Dict[Path, List[Any]]:

    grouped: Dict[Path, List[Any]] = defaultdict(list)

    for entry in entries:
        grouped[entry.rebased_path].append(entry)

    def sort_key(entry):

        if entry.source in ("base", "linear"):
            return 0

        if entry.source.startswith("variant:"):

            try:
                return int(entry.source.split(":")[1]) + 1

            except Exception:
                raise ValueError(
                    f"Invalid variant source: {entry.source}"
                )

        raise ValueError(
            f"Unknown config source: {entry.source}"
        )

    for path in grouped:
        grouped[path].sort(key=sort_key)

    return grouped


# ---------------------------------------------------------
# Merge logic
# ---------------------------------------------------------

def _merge_ordered_entries(
    entries: List[Any],
) -> dict:

    configs = []

    for entry in entries:

        config_data = _load_config_entry(entry)

        logger.debug(
            "Loaded config from %s (%s)",
            entry.real_path,
            entry.source,
        )

        configs.append(config_data)

    result = configs[0] if configs else {}

    for override in configs[1:]:

        result = deep_merge_dicts(
            result,
            override,
        )

    return result


# ---------------------------------------------------------
# Tree insertion (pure virtual path)
# ---------------------------------------------------------

def _insert_into_tree(
    root: ConfigNode,
    scope_path: Path,
    config_data: dict,
):
    """
    Insert config into tree using virtual path (rebased_path).
    """

    parts = scope_path.parts

    current = root

    for i, part in enumerate(parts):

        current_path = Path(*parts[:i + 1])

        current = current.ensure_child(
            part,
            current_path,
        )

    current.config = config_data


# ---------------------------------------------------------
# Config loading
# ---------------------------------------------------------

def _load_config_entry(
    entry: FileEntry,
) -> dict:
    """
    Load config from FileEntry.

    Currently supports filesystem-backed configs only.
    """

    if entry.real_path is None:

        raise RuntimeError(
            f"Config entry {entry.rebased_path} "
            f"has no real_path (unsupported)"
        )

    return _load_config_with_ref(entry.real_path)


def _load_config_with_ref(
    config_path: Path,
) -> dict:

    data = load_json(config_path)

    if "$REF" not in data:
        return data

    ref_path = (
        config_path.parent / data["$REF"]
    ).resolve()

    if not ref_path.is_file():

        raise FileNotFoundError(
            f"Referenced config file not found: {ref_path}"
        )

    base_data = load_json(ref_path)

    override_data = {
        k: v
        for k, v in data.items()
        if k != "$REF"
    }

    return deep_merge_dicts(
        base_data,
        override_data,
    )