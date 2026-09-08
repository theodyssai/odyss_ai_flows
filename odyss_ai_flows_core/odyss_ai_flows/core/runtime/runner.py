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
from typing import Any, Dict, Optional, List, Union
import re

import asyncio
import traceback

from odyss_ai_flows.core.runtime.inputs import (
    set_inputs,
    set_injected_results,
    wrap_sensitive_inputs,
)

from odyss_ai_flows.core.files.api import (
    init_file_repo,
)

from odyss_ai_flows.core.config.api import (
    init_config_for_current_scope,
    cget,
    pre_resolve_config_tree_async,
    get_node_scope,
)

from odyss_ai_flows.core.config.context import (
    config as _config,
)

from odyss_ai_flows.core.builder.builder import (
    build_and_initialize_structure,
)

from odyss_ai_flows.core.executor.executor import (
    FlowExecutor,
)

from odyss_ai_flows.core.executor.cycle_passive_detector import (
    analyze_cycles,
)

from odyss_ai_flows.core.executor.raw_flow_result import (
    RawFlowResult,
    FlowStatus,
)

from odyss_ai_flows.core.runtime.flow_result import (
    FlowResult,
)

from odyss_ai_flows.core.utils.logger import (
    logger,
)

from odyss_ai_flows.core.executor.exceptions import (
    FrameworkError,
)

from odyss_ai_flows.core.runtime.run_context import (
    ensure_top_run_state,
    next_index_for_scope,
    set_run_name,
    RUN_NAME,
)

from odyss_ai_flows.core.runtime.prepared_flow import (
    PreparedFlow,
)

from odyss_ai_flows.core.executor.strategy import (
    WorkStrategy,
    DefaultWorkStrategy,
    LeasedConcurrencyStrategy,
)

from odyss_ai_flows.core.runtime.strategy_registry import (
    get_default_strategy_factory,
)

from odyss_ai_flows.core.executor.execution_context import (
    get_executor,
)


# ---------------------------------------------------------
# Lease-aware task wrapper
# ---------------------------------------------------------

class LeaseAwareTask:
    """
    Awaitable task wrapper that temporarily yields orchestration
    execution policy while awaiting the underlying task.

    Important:
    - Creating the task does NOT yield orchestration.
    - Awaiting the task DOES yield orchestration.
    - Strategy owns the actual suspension semantics.
    """

    def __init__(
        self,
        task: asyncio.Task[FlowResult],
        strategy: WorkStrategy,
    ):
        self._task = task
        self._strategy = strategy

    # -----------------------------------------------------

    def __await__(self):

        async def wait():

            return await (
                self._strategy
                .await_with_policy(
                    self._task
                )
            )

        return wait().__await__()

    # -----------------------------------------------------
    # Transparent delegation helpers
    # -----------------------------------------------------

    def done(self) -> bool:
        return self._task.done()

    def cancel(self) -> bool:
        return self._task.cancel()

    def cancelled(self) -> bool:
        return self._task.cancelled()

    def result(self) -> FlowResult:
        return self._task.result()

    def exception(self):
        return self._task.exception()

    def get_name(self) -> str:
        return self._task.get_name()

    def set_name(self, value: str) -> None:
        self._task.set_name(value)

    @property
    def raw_task(self) -> asyncio.Task[FlowResult]:
        return self._task


# ---------------------------------------------------------
# Result handling
# ---------------------------------------------------------

def _handle_result(
    result: RawFlowResult,
    raise_on_fail: bool,
) -> None:

    err = result.error

    # -----------------------------------------------------
    # Logging
    # -----------------------------------------------------

    if err is not None:

        if isinstance(err, BaseException):

            tb_text = "".join(
                traceback.TracebackException
                .from_exception(err)
                .format()
            ).rstrip()

            logger.error(
                "%s\n%s",
                err,
                tb_text,
            )

        else:

            logger.error(
                "%r",
                err,
            )

    # -----------------------------------------------------
    # FrameworkError propagation
    # -----------------------------------------------------

    if (
        result.status is FlowStatus.ERROR
        and result.error is not None
    ):

        if isinstance(
            result.error,
            FrameworkError,
        ):
            raise result.error

        raise FrameworkError(
            result.error
        ) from result.error

    # -----------------------------------------------------
    # raise_on_fail policy
    # -----------------------------------------------------

    if (
        raise_on_fail
        and result.status not in (
            FlowStatus.SUCCESS,
            FlowStatus.BREAK,
        )
    ):
        raise result.error


# ---------------------------------------------------------
# Strategy resolution
# ---------------------------------------------------------

def _resolve_strategy(
    *,
    strategy: Optional[WorkStrategy],
    max_concurrency: Optional[int],
    parent_executor: Optional[FlowExecutor],
) -> WorkStrategy:

    # -----------------------------------------------------
    # Explicit conflict
    # -----------------------------------------------------

    if (
        strategy is not None
        and max_concurrency is not None
    ):
        raise ValueError(
            "Cannot specify both "
            "'strategy' and "
            "'max_concurrency'"
        )

    # -----------------------------------------------------
    # Explicit strategy
    # -----------------------------------------------------

    if strategy is not None:

        return strategy

    # -----------------------------------------------------
    # Explicit leased strategy
    # -----------------------------------------------------

    if (
        max_concurrency is not None
        and max_concurrency > 0
    ):

        return LeasedConcurrencyStrategy(
            max_concurrency
        )

    # -----------------------------------------------------
    # Nested inheritance
    # -----------------------------------------------------

    if parent_executor is not None:

        return parent_executor.strategy

    # -----------------------------------------------------
    # Global default strategy factory
    # -----------------------------------------------------

    factory = (
        get_default_strategy_factory()
    )

    if factory is not None:

        resolved = factory()

        if not isinstance(
            resolved,
            WorkStrategy,
        ):
            raise TypeError(
                "Default strategy factory "
                "must return WorkStrategy"
            )

        return resolved

    # -----------------------------------------------------
    # Fallback
    # -----------------------------------------------------

    return DefaultWorkStrategy()


# ---------------------------------------------------------
# Runner
# ---------------------------------------------------------

def _normalize_scope_for_display(scope: str) -> str:
    parts = [part for part in re.split(r"[\\/]+", scope) if part]
    return "/".join(parts)


def run_flow(
    flow: Union[
        str,
        Path,
        PreparedFlow,
    ],

    inputs: Optional[
        Dict[str, Any]
    ] = None,

    run_name: Optional[
        str
    ] = None,

    variant_paths: Optional[
        List[Union[str, Path]]
    ] = None,

    raise_on_fail: bool = True,

    pre_resolve_config: Optional[
        bool
    ] = None,

    provided_tree: Optional[
        dict
    ] = None,

    strategy: Optional[
        WorkStrategy
    ] = None,

    max_concurrency: Optional[
        int
    ] = None,

    target_node: Optional[str] = None,

    injected_results: Optional[
        Dict[str, Any]
    ] = None,

    **kwargs: Any,
) -> LeaseAwareTask:
    """
    Execute a flow.

    Supported inputs:
        - Path / str → filesystem flow
        - PreparedFlow → virtual or hybrid flow

    Config sources:
        - explicit provided_tree argument
        - PreparedFlow.config_tree
        - filesystem config scan
    """

    # -----------------------------------------------------
    # Parent execution context
    # -----------------------------------------------------

    parent_executor = (
        get_executor()
    )

    # -----------------------------------------------------
    # Normalize flow input
    # -----------------------------------------------------

    prepared: Optional[
        PreparedFlow
    ]

    prepared_tree = None

    if isinstance(
        flow,
        PreparedFlow,
    ):

        prepared = flow

        base_path = (
            Path(flow.base_path)
            if flow.base_path
            else None
        )

        prepared_tree = (
            flow.config_tree
        )

    else:

        prepared = None
        base_path = Path(flow)

    # -----------------------------------------------------
    # Config tree precedence
    # -----------------------------------------------------

    effective_tree = (

        provided_tree

        if provided_tree is not None

        else prepared_tree
    )

    # -----------------------------------------------------
    # Variants
    # -----------------------------------------------------

    variant_paths = (

        [Path(p) for p in variant_paths]

        if variant_paths

        else None
    )

    # -----------------------------------------------------
    # Inputs
    # -----------------------------------------------------

    combined_inputs = {

        **(inputs or {}),
        **kwargs,
    }

    node_scope = (
        get_node_scope()
    )

    # -----------------------------------------------------
    # Run naming
    # -----------------------------------------------------

    if node_scope is None:

        state = ensure_top_run_state(
            explicit_top_name=run_name
        )

        effective_run_name = (
            state.top_run_name
        )

    else:

        state = ensure_top_run_state()

        if run_name:

            effective_run_name = (
                run_name
            )

        else:

            normalized_scope = _normalize_scope_for_display(
                node_scope
            )

            idx = next_index_for_scope(
                normalized_scope
            )

            effective_run_name = (

                f"{state.top_run_name}, "

                f"nested in: {normalized_scope}, "

                f"index: {idx}"
            )

    # -----------------------------------------------------
    # Strategy resolution
    # -----------------------------------------------------

    resolved_strategy = (
        _resolve_strategy(
            strategy=strategy,
            max_concurrency=max_concurrency,
            parent_executor=parent_executor,
        )
    )

    # -----------------------------------------------------
    # Execution task
    # -----------------------------------------------------

    async def _run_in_task() -> FlowResult:

        set_run_name(
            effective_run_name
        )

        try:

            # -------------------------------------------------
            # Inputs
            # -------------------------------------------------

            wrapped_inputs = (
                await wrap_sensitive_inputs(
                    combined_inputs
                )
            )

            set_inputs(
                wrapped_inputs
            )

            if injected_results is not None:
                set_injected_results(
                    injected_results
                )

            # -------------------------------------------------
            # File repository
            # -------------------------------------------------

            init_file_repo(
                flow_path=base_path,
                variant_paths=variant_paths,
                prepared=prepared,
            )

            # -------------------------------------------------
            # Config
            # -------------------------------------------------

            await init_config_for_current_scope(
                provided_tree=effective_tree
            )

            effective_pre_resolve = (

                pre_resolve_config

                if pre_resolve_config
                is not None

                else await cget(
                    "config.pre_resolve",
                    default=False,
                )
            )

            if effective_pre_resolve:

                await pre_resolve_config_tree_async()

            # -------------------------------------------------
            # Build + Execute
            # -------------------------------------------------

            structure = (
                await build_and_initialize_structure(
                    base_path or Path(".")
                )
            )

            passive_cycle_detection = await _config.get(
                "execution.passive_cycle_detection",
                default=True,
            )

            if passive_cycle_detection:
                analyze_cycles(structure)

            executor = FlowExecutor(
                structure=structure,
                strategy=resolved_strategy,
            )

        except Exception as e:

            raise FrameworkError(
                e
            ) from e

        try:

            # -------------------------------------------------
            # Execution phase
            # -------------------------------------------------

            raw_result: RawFlowResult = (
                await executor.run(target_node)
            )

        except Exception as e:

            raise FrameworkError(
                e
            ) from e

        # -----------------------------------------------------
        # Post-processing
        # -----------------------------------------------------

        _handle_result(
            raw_result,
            raise_on_fail,
        )

        return FlowResult(
            raw_result
        )

    # -----------------------------------------------------
    # Create actual execution task
    # -----------------------------------------------------

    task = asyncio.create_task(
        _run_in_task()
    )

    if parent_executor is None:
        return task

    return LeaseAwareTask(
        task=task,
        strategy=resolved_strategy,
    )