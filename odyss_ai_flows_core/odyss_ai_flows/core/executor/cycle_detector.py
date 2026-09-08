# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
from collections import deque
from typing import Optional

from odyss_ai_flows.core.executor.exceptions import CycleDetectedError


class _TrackContext:
    def __init__(self, detector: "CycleDetector", caller: str, target: str):
        self._detector = detector
        self._caller = caller
        self._target = target

    def __enter__(self):
        cycle = self._detector._find_cycle_path(self._caller, self._target)
        if cycle is not None:
            raise CycleDetectedError(cycle)
        targets = self._detector._waiting_for.setdefault(self._caller, {})
        targets[self._target] = targets.get(self._target, 0) + 1
        return self

    def __exit__(self, *_):
        targets = self._detector._waiting_for.get(self._caller, {})
        if self._target in targets:
            targets[self._target] -= 1
            if targets[self._target] <= 0:
                del targets[self._target]
        if not targets:
            del self._detector._waiting_for[self._caller]


class CycleDetector:
    def __init__(self):
        self._waiting_for: dict[str, dict[str, int]] = {}

    def track(self, caller: str, target: str) -> _TrackContext:
        return _TrackContext(self, caller, target)

    def _find_cycle_path(self, caller: str, target: str) -> Optional[list[str]]:
        if caller == target:
            return [caller, target]

        parents: dict[str, Optional[str]] = {target: None}
        queue: deque[str] = deque([target])

        while queue:
            current = queue.popleft()
            if current == caller:
                path = []
                node: Optional[str] = current
                while node is not None:
                    path.append(node)
                    node = parents[node]
                path.reverse()
                return [caller] + path

            for nxt in self._waiting_for.get(current, {}):
                if nxt not in parents:
                    parents[nxt] = current
                    queue.append(nxt)

        return None
