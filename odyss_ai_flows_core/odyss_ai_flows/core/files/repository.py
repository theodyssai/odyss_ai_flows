# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable, Any
from collections import defaultdict

from odyss_ai_flows.core.utils.logger import logger


@dataclass(frozen=True)
class FileEntry:
    real_path: Optional[Path]
    rebased_path: Path
    kind: str
    name: Optional[str] = None
    source: Optional[str] = None

    # New virtual capabilities
    content: Optional[str] = None
    callable_obj: Optional[Callable[..., Any]] = None
    redirected_path: Optional[Path] = None


class FileRepository:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.entries: List[FileEntry] = []
        self.by_kind: Dict[str, List[FileEntry]] = defaultdict(list)
        self.by_rebased: Dict[Path, FileEntry] = {}
        self.by_kind_and_name: Dict[Tuple[str, str], FileEntry] = {}

    # ------------------------------------------------------------------
    # Core add logic (unchanged)
    # ------------------------------------------------------------------

    def add(self, entry: FileEntry):
        key = entry.rebased_path
        existing = self.by_rebased.get(key)
        is_config = entry.kind.startswith("config:")

        if existing and not is_config:
            action = "OVERRIDE"

            self.entries.remove(existing)

            self.by_kind[
                existing.kind
            ].remove(existing)

            # -----------------------------------------
            # Remove stale name mapping
            # -----------------------------------------

            if existing.name is not None:

                self.by_kind_and_name.pop(

                    (
                        existing.kind,
                        str(existing.name),
                    ),

                    None,
                )
        elif existing and is_config:
            action = "MERGE"
        else:
            action = "NEW"

        self.entries.append(entry)
        self.by_kind[entry.kind].append(entry)

        if not is_config or not existing:
            self.by_rebased[key] = entry

        if entry.name is not None:
            self.by_kind_and_name[
                (entry.kind, str(entry.name))
            ] = entry

        logger.debug(
            f"{action:<8} | kind={entry.kind:<14} | name={str(entry.name):<15} "
            f"| rebased={entry.rebased_path} | real={entry.real_path} | from={entry.source}"
        )

    # ------------------------------------------------------------------
    # New: fset
    # ------------------------------------------------------------------

    def fset(self, path: Path | str, value: Any):
        from odyss_ai_flows.core.files.entry_builder import build_file_entry

        path = Path(path)

        entry = build_file_entry(
            rebased_path=path,
            real_path=None,
            source="fset",
            value=value,
        )

        self.add(entry)

    # ------------------------------------------------------------------
    # Queries (unchanged)
    # ------------------------------------------------------------------

    def get_by_kind(self, kind: str) -> List[FileEntry]:
        return self.by_kind.get(kind, [])

    def get_by_kind_and_name(self, kind: str, name: str) -> Optional[FileEntry]:
        return self.by_kind_and_name.get((kind, name))

    def get_by_rebased(self, rebased: Path) -> Optional[FileEntry]:
        return self.by_rebased.get(rebased)

    def get_all(self) -> List[FileEntry]:
        return list(self.entries)