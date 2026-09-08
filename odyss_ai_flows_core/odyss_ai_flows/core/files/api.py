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
import contextvars

from odyss_ai_flows.core.files.repository import FileEntry, FileRepository
from odyss_ai_flows.core.files.scanner import (
    scan_repository_with_variants,
    scan_single_file_repo,
)
from odyss_ai_flows.core.utils.logger import logger
from typing import List, Optional, overload, TYPE_CHECKING

if TYPE_CHECKING:
    from odyss_ai_flows.core.runtime.prepared_flow import PreparedFlow


_CURRENT_REPO = contextvars.ContextVar("CURRENT_REPO")


def set_file_repo(repo: FileRepository):
    _CURRENT_REPO.set(repo)


def init_file_repo(
    flow_path: Optional[Path],
    variant_paths: Optional[List[Path]] = None,
    prepared: Optional["PreparedFlow"] = None,
):
    variant_paths = variant_paths or []

    logger.info("Initializing file repository...")
    logger.debug(f"Flow path: {flow_path}")
    logger.debug(f"Variant paths: {variant_paths}")
    logger.debug(f"Prepared flow: {'yes' if prepared else 'no'}")

    has_tree = prepared is not None and prepared.config_tree is not None

    # ---------------------------------------------------------
    # Base repository creation
    # ---------------------------------------------------------

    if flow_path is None:
        # pure virtual flow → no scan
        repo = FileRepository(base_path=Path("."))
    else:
        include_config = not has_tree

        if flow_path.is_file():
            repo = scan_single_file_repo(
                flow_path,
                include_config=include_config,
            )
        else:
            repo = scan_repository_with_variants(
                flow_path=flow_path,
                variant_paths=variant_paths,
                include_config=include_config,
            )

    # ---------------------------------------------------------
    # Apply PreparedFlow mutations
    # ---------------------------------------------------------

    if prepared is not None:
        prepared.apply(repo)

    # ---------------------------------------------------------
    # Finalize
    # ---------------------------------------------------------

    set_file_repo(repo)


# ---------------------------------------------------------
# fget (unchanged)
# ---------------------------------------------------------

@overload
def fget(kind: str) -> List[FileEntry]: ...
@overload
def fget(kind: str, *, name: str) -> Optional[FileEntry]: ...
@overload
def fget(kind: str, *, rebased_path: Path) -> Optional[FileEntry]: ...


def fget(kind: str, *, name: Optional[str] = None, rebased_path: Optional[Path] = None):
    repo = _CURRENT_REPO.get(None)
    if not repo:
        raise RuntimeError("fget() used without FileRepository set")

    if (name is not None) and (rebased_path is not None):
        raise ValueError("Provide only one of name= or rebased_path=.")

    if name is not None:
        return repo.get_by_kind_and_name(kind, name)

    if rebased_path is not None:
        return repo.get_by_rebased(rebased_path)

    return repo.get_by_kind(kind)