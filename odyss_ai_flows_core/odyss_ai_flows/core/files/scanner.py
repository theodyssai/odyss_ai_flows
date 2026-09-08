# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
from pathlib import Path
import os

from odyss_ai_flows.core.files.repository import FileRepository, FileEntry
from odyss_ai_flows.core.utils.logger import logger
from odyss_ai_flows.core.files.entry_builder import build_file_entry

ROOT = Path.cwd().resolve()
SKIP_DIRS = [".cataloghouse", "__pycache__", "unused"]


def _get_relative(path: Path) -> Path:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT)
    except ValueError:
        return resolved


# ---------------------------------------------------------
# MAIN SCAN
# ---------------------------------------------------------

def scan_repository_with_variants(
    flow_path: Path,
    variant_paths: list[Path],
    *,
    include_config: bool = True,
) -> FileRepository:
    logger.info("Starting repository scan...")

    flow_path = flow_path.resolve()
    is_under_root = _is_under_root(flow_path)

    rel_flow_path = _get_relative(flow_path)
    rel_variant_paths = [_get_relative(vp) for vp in variant_paths]

    logger.debug(f"Execution root: {ROOT}")
    logger.debug(f"Flow path: {rel_flow_path}")
    logger.debug(f"Variant paths: {rel_variant_paths}")
    logger.debug(f"Include config: {include_config}")

    if not is_under_root:
        logger.warning(
            "Flow path %s is outside ROOT %s — skipping linear config scan",
            flow_path, ROOT
        )

    repo = FileRepository(base_path=rel_flow_path)

    if include_config and is_under_root:
        _scan_linear_config_path(rel_flow_path, repo)

    _scan_dir_tree(
        rel_flow_path,
        rel_flow_path,
        "base",
        repo,
        include_config=include_config,
    )

    for i, variant_root in enumerate(rel_variant_paths):
        _scan_dir_tree(
            variant_root,
            rel_flow_path,
            f"variant:{i}",
            repo,
            include_config=include_config,
        )

    logger.info(f"Scan complete. Total files: {len(repo.get_all())}")
    return repo


# ---------------------------------------------------------
# SINGLE FILE SCAN
# ---------------------------------------------------------

def scan_single_file_repo(
    node_file: Path,
    *,
    include_config: bool = True,
) -> FileRepository:
    logger.info("Scanning single file repository...")

    node_file = node_file.resolve()
    is_under_root = _is_under_root(node_file)

    rel_file = _get_relative(node_file)
    rel_dir = rel_file.parent
    stem = rel_file.stem

    repo = FileRepository(base_path=rel_dir)

    if not is_under_root:
        logger.warning(
            "Node file %s is outside ROOT %s — skipping linear config scan",
            node_file, ROOT
        )

    if include_config and is_under_root:
        _scan_linear_config_path(rel_dir, repo)

    _match_and_add(
        rel_file,
        rel_file,
        "base",
        repo,
        include_config=include_config,
    )

    if include_config:
        for fname in [f"{stem}.config.json", f"{stem}.model.py"]:
            candidate = ROOT / rel_dir / fname
            if candidate.is_file():
                rel = _get_relative(candidate)
                _match_and_add(
                    rel,
                    rel,
                    "base",
                    repo,
                    include_config=include_config,
                )

    general_config = ROOT / rel_dir / "config.json"

    if general_config.is_file():

        rel = _get_relative(general_config)

        _match_and_add(
            rel,
            rel,
            "base",
            repo,
            include_config=include_config,
        )

    return repo


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def _is_under_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT)
        return True
    except ValueError:
        return False


def _scan_linear_config_path(to_path: Path, repo: FileRepository):
    current = Path(".")
    for part in to_path.parts[:-1]:
        current_dir = current / part
        config_file = ROOT / current_dir / "config.json"
        if config_file.is_file():
            repo.add(FileEntry(
                real_path=current_dir / "config.json",
                rebased_path=current_dir,
                kind="config:folder",
                source="linear"
            ))
        current = current_dir


def _scan_dir_tree(
    scan_root: Path,
    base_path: Path,
    source_label: str,
    repo: FileRepository,
    *,
    include_config: bool,
):
    abs_scan_root = ROOT / scan_root

    for dirpath, dirnames, filenames in os.walk(abs_scan_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        current_dir = Path(dirpath).relative_to(ROOT)

        for fname in filenames:
            real_path = current_dir / fname
            relative_within_variant = real_path.relative_to(scan_root)
            rebased_path = base_path / relative_within_variant

            _match_and_add(
                real_path,
                rebased_path,
                source_label,
                repo,
                include_config=include_config,
            )


def _match_and_add(
    real_path: Path,
    rebased_path: Path,
    source: str,
    repo: FileRepository,
    *,
    include_config: bool,
):
    entry = build_file_entry(
    rebased_path=rebased_path,
    real_path=real_path,
    source=source,
)

# ---------------------------------------------------------
# Normalize folder config semantic identity
# config.json represents scope directory,
# not the physical config file itself.
# ---------------------------------------------------------

    if entry.kind == "config:folder":

        entry = FileEntry(
            real_path=entry.real_path,
            rebased_path=rebased_path.parent,
            kind=entry.kind,
            name=entry.name,
            source=entry.source,
            content=entry.content,
            callable_obj=entry.callable_obj,
            redirected_path=entry.redirected_path,
        )

    if not include_config and entry.kind.startswith("config:"):
        return

    repo.add(entry)