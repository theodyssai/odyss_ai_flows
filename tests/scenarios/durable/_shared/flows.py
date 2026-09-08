from __future__ import annotations

from pathlib import Path

_HOST_ROOT = Path(__file__).resolve().parent.parent
_FLOWS_DIR = _HOST_ROOT / "_flows"


def host_relative(path: Path) -> str:
    return path.resolve().relative_to(_HOST_ROOT).as_posix()


def flow_path(name: str) -> str:
    return host_relative(_FLOWS_DIR / name)
