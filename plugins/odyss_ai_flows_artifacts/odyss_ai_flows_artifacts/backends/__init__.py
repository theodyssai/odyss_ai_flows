from typing import Callable, Dict

from odyss_ai_flows_artifacts.backends.base import (
    ArtifactFieldUpdate,
    ArtifactRow,
    Backend,
    CommitPayload,
    JournalEntry,
)


_REGISTRY: Dict[str, Callable[..., Backend]] = {}


def register_backend(name: str, factory: Callable[..., Backend]) -> None:
    _REGISTRY[name] = factory


def get_backend_factory(name: str) -> Callable[..., Backend]:
    if name not in _REGISTRY:
        raise KeyError(
            f"No backend registered under name {name!r}. "
            f"Known: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]


__all__ = [
    "ArtifactFieldUpdate",
    "ArtifactRow",
    "Backend",
    "CommitPayload",
    "JournalEntry",
    "register_backend",
    "get_backend_factory",
]
