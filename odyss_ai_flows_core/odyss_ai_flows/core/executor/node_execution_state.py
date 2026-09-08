# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
import asyncio
from typing import Any, Optional

from odyss_ai_flows.core.builder.types import FlowNode
from odyss_ai_flows.core.config.api import cget
from odyss_ai_flows.core.executor.exceptions import FlowBreak, FrameworkError, NodeExecutionError
from odyss_ai_flows.core.executor.failure_latch import get_latch
from odyss_ai_flows.core.executor.execution_context import set_current_node_name, reset_current_node_name


class NodeExecutionState:
    def __init__(self, node: FlowNode, lazy: bool = False):
        self.node = node
        self.task: Optional[asyncio.Task] = None
        self.result: Any = None
        self.error: Optional[BaseException] = None
        self.completed: bool = False
        self.lazy: bool = lazy
        self.done_event: asyncio.Event = asyncio.Event()

    async def determine_lazy(self):
        self.lazy = await cget("execution.lazy", default=False, scope=self.node.scope)

    async def run(self, strategy):
        token = set_current_node_name(self.node.name)
        try:
            self.result = await strategy.run_node(
                self.node.scope,
                self.node.handler.run
            )
            self.completed = True
            self.done_event.set()

        except asyncio.CancelledError:
            raise

        except FlowBreak as e:
            if not hasattr(e, "node_scope") or e.node_scope is None:
                e.node_scope = self.node.scope
            self.error = e
            get_latch().claim(e)
            raise

        except FrameworkError as e:
            self.error = e
            get_latch().claim(e)
            raise

        except NodeExecutionError as e:
            self.error = e
            get_latch().claim(e)
            raise

        except BaseException as e:
            wrapped = NodeExecutionError(self.node.scope, e)
            self.error = wrapped
            get_latch().claim(wrapped)
            raise wrapped from e

        finally:
            reset_current_node_name(token)
