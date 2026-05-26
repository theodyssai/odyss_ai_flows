# tests/tests_runtime/global_config.py

from __future__ import annotations

import json

from pathlib import Path

from odyss_ai_flows.core.config.utils import (
    deep_merge_dicts,
)


# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

GLOBAL_CONFIG_FILENAME = (
    "global_config.json"
)

SCENARIO_META_FILENAME = (
    "global_config.meta.json"
)

SHARED_DEFAULTS_PATH = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    / "test_shared"
    / "global_config.base.json"
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _load_json(
    path: Path,
) -> dict:

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

def prepare_global_config(
    scenario_dir: Path,
) -> Path | None:

    shared = {}

    if SHARED_DEFAULTS_PATH.is_file():

        shared = _load_json(
            SHARED_DEFAULTS_PATH
        )

    meta_path = (
        scenario_dir
        / SCENARIO_META_FILENAME
    )

    scenario = {}

    if meta_path.is_file():

        scenario = _load_json(
            meta_path
        )

    if not shared and not scenario:
        return None

    merged = deep_merge_dicts(
        shared,
        scenario,
    )

    output_path = (
        Path.cwd()
        / GLOBAL_CONFIG_FILENAME
    )

    output_path.write_text(
        json.dumps(
            merged,
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return output_path


def cleanup_global_config(
    generated_path: Path | None,
) -> None:

    if generated_path is None:
        return

    if generated_path.exists():
        generated_path.unlink()