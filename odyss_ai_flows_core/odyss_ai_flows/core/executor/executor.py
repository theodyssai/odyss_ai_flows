# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# ai@bydlow.ski
import asyncio
from typing import Any, Optional, Awaitable

from odyss_ai_flows.core.executor.raw_flow_result import RawFlowResult, FlowStatus
from odyss_ai_flows.core.executor.exceptions import FlowBreak, NodeExecutionError
from odyss_ai_flows.core.executor.strategy import WorkStrategy
from odyss_ai_flows.core.executor.node_execution_state import NodeExecutionState
from odyss_ai_flows.core.builder.types import FlowStructure
from odyss_ai_flows.core.utils.logger import logger
from odyss_ai_flows.core.executor.execution_context import set_executor, get_current_node_name
from odyss_ai_flows.core.executor.cycle_detector import CycleDetector
from odyss_ai_flows.core.executor.failure_latch import FailureLatch, _current_latch, get_latch
from odyss_ai_flows.core.runtime.inputs import get_injected_results
from pathlib import Path


async def _sentinel() -> None:
    return None


class FlowExecutor:
    def __init__(
        self,
        structure: FlowStructure,
        strategy: WorkStrategy,
    ):
        self.structure = structure
        self.strategy = strategy

        self.node_states: dict[
            str,
            NodeExecutionState,
        ] = {}

        self._tg: Optional[
            asyncio.TaskGroup
        ] = None

        # -------------------------------------------------
        # Dual resolver maps
        # -------------------------------------------------

        self.path_to_node_map: dict[
            Path,
            list[str],
        ] = {}

        self.callable_to_node_map: dict[
            int,
            list[str],
        ] = {}

        self.cycle_detector = CycleDetector()

    def _create_managed_task(self, coro: Awaitable[Any]) -> asyncio.Task:
        latch = get_latch()
        if latch.is_set():
            raise asyncio.CancelledError()

        tg = self._tg
        if tg is None:
            raise asyncio.CancelledError()

        try:
            return tg.create_task(coro)
        except RuntimeError:
            raise asyncio.CancelledError()

    # ---------------------------------------------------------

    async def _init_node_states(self) -> None:
        for node in self.structure.nodes.values():
            state = NodeExecutionState(node)
            await state.determine_lazy()
            self.node_states[node.name] = state

            entry = node.entry  # ← assumed after your builder refactor

            # --- PATH-BASED RESOLUTION ---
            path = None
            if entry.redirected_path:
                path = Path(entry.redirected_path).resolve()
            elif entry.real_path:
                path = Path(entry.real_path).resolve()

            if path:
                self.path_to_node_map.setdefault(path, []).append(node.name)

            # --- CALLABLE-BASED RESOLUTION ---
            if entry.callable_obj is not None:
                key = id(entry.callable_obj)
                self.callable_to_node_map.setdefault(key, []).append(node.name)

    # ---------------------------------------------------------

    async def run(self, target_node: Optional[str] = None) -> RawFlowResult:

        # --- Build node states and resolver maps ---
        await self._init_node_states()

        if target_node is not None:
            injected = get_injected_results() or {}
            for dep_name, dep_result in injected.items():
                state = self.node_states.get(dep_name)
                if state is None:
                    continue
                state.result = dep_result
                state.completed = True
                state.done_event.set()
                state.task = asyncio.create_task(_sentinel())

        set_executor(self)

        # --- Outcome tracking ---
        status: FlowStatus = FlowStatus.SUCCESS
        primary_error: Optional[BaseException] = None
        suppressed_error: Optional[BaseException] = None

        latch = FailureLatch()
        _current_latch.set(latch)

        taskgroup_failed = False

        try:
            async with asyncio.TaskGroup() as tg:
                self._tg = tg

                if target_node is not None:
                    target_state = self.node_states[target_node]
                    target_state.task = tg.create_task(target_state.run(self.strategy))
                else:
                    for state in self.node_states.values():
                        if not state.lazy:
                            state.task = tg.create_task(state.run(self.strategy))
                    logger.info("Flow executed successfully")

        except BaseExceptionGroup as eg:
            suppressed_error = eg
            taskgroup_failed = True

        except Exception as e:
            suppressed_error = e
            taskgroup_failed = True

        finally:
            self._tg = None

        # --- Determine final status ---
        if taskgroup_failed:
            latched = latch.get()

            if latched is not None:
                if isinstance(latched, FlowBreak):
                    status = FlowStatus.BREAK
                    primary_error = latched
                elif isinstance(latched, NodeExecutionError):
                    status = FlowStatus.FAILURE
                    primary_error = latched
                else:
                    status = FlowStatus.ERROR
                    primary_error = latched
            else:
                status = FlowStatus.ERROR
                primary_error = suppressed_error

        # --- Collect results ---
        results = {
            state.node.name: state.result
            for state in self.node_states.values()
            if state.completed
        }

        return RawFlowResult(
            status=status,
            results=results,
            path_to_node_map={k: v.copy() for k, v in self.path_to_node_map.items()},
            callable_to_node_map={k: v.copy() for k, v in self.callable_to_node_map.items()},
            error=primary_error,
            suppressed_error=suppressed_error,
        )

    # ---------------------------------------------------------

    async def get_node_result(self, name: str) -> Any:
        state = self.node_states.get(name)
        if not state:
            raise RuntimeError(f"Node '{name}' not found")

        if state.done_event.is_set():
            return state.result

        if get_latch().is_set():
            raise asyncio.CancelledError()

        if state.task is None:
            if not state.lazy:
                raise RuntimeError(
                    f"Node '{name}' was not prelaunched and is not marked as lazy."
                )
            logger.info("Launching lazy node: %s", name)
            state.task = self._create_managed_task(state.run(self.strategy))

        caller = get_current_node_name()
        if caller is not None:
            with self.cycle_detector.track(caller, name):
                await state.done_event.wait()
        else:
            await state.done_event.wait()

        return state.result

    # ---------------------------------------------------------

    async def await_dependency(self, name: str) -> Any:
        return await self.strategy.await_with_policy(
            self.get_node_result(name)
        )