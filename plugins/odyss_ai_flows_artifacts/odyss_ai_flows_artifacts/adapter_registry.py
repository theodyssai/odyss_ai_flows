import importlib.resources
import importlib.util
import os
from functools import lru_cache
from typing import Any, Dict, Optional


BUILT_IN_PACKAGE = "odyss_ai_flows_artifacts.built_in_adapters"


_GLOBAL_ADAPTERS: Dict[str, Any] = {}


def register_adapter(name: str, module_or_callable) -> None:
    _GLOBAL_ADAPTERS[name] = module_or_callable


@lru_cache(maxsize=1)
def _scan_built_in_adapters() -> frozenset:
    try:
        files = importlib.resources.files(BUILT_IN_PACKAGE)
    except (ModuleNotFoundError, FileNotFoundError):
        return frozenset()
    names = set()
    for entry in files.iterdir():
        name = entry.name
        if name.endswith(".py") and name != "__init__.py":
            names.add(name[:-3])
    return frozenset(names)


class AdapterRegistry:
    def __init__(
        self,
        adapters_path: Optional[str] = None,
        adapter_mapping: Optional[Dict[str, str]] = None,
    ):
        self.adapters_path = adapters_path
        self.adapter_mapping = adapter_mapping or {}
        self._cache: Dict[str, Any] = {}
        self._registered: Dict[str, Any] = {}

    def register(self, name: str, module_or_callable) -> None:
        self._registered[name] = module_or_callable
        self._cache.pop(name, None)

    def known_names(self) -> set:
        names = set(_scan_built_in_adapters())
        names.update(_GLOBAL_ADAPTERS.keys())
        names.update(self._registered.keys())
        if self.adapters_path and os.path.isdir(self.adapters_path):
            for f in os.listdir(self.adapters_path):
                if f.endswith(".py") and f != "__init__.py":
                    names.add(f[:-3])
        return names

    def _resolve(self, name: str) -> str:
        return self.adapter_mapping.get(name, name)

    def load(self, name: str):
        if name in self._cache:
            return self._cache[name]

        if name in self._registered:
            mod = self._registered[name]
            self._cache[name] = mod
            return mod

        if name in _GLOBAL_ADAPTERS:
            mod = _GLOBAL_ADAPTERS[name]
            self._cache[name] = mod
            return mod

        resolved = self._resolve(name)

        if self.adapters_path:
            path = os.path.join(self.adapters_path, f"{resolved}.py")
            if os.path.isfile(path):
                spec = importlib.util.spec_from_file_location(resolved, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self._cache[name] = module
                return module

        if resolved in _scan_built_in_adapters():
            module = importlib.import_module(f"{BUILT_IN_PACKAGE}.{resolved}")
            self._cache[name] = module
            return module

        raise LookupError(f"Adapter {name!r} (resolved: {resolved!r}) not found")
