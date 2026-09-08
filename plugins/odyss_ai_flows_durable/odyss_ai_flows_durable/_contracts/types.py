from __future__ import annotations

from collections.abc import Generator

from typing import Any, TypeAlias, TypeVar


T = TypeVar("T")

DurableTask: TypeAlias = Any

DurableGenerator: TypeAlias = Generator[Any, Any, T]
