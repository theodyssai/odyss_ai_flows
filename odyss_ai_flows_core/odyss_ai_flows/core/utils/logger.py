# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
import logging
import os
import sys
import io
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv, find_dotenv

# ============================================================
# Environment bootstrap (dev convenience only)
# ============================================================

load_dotenv(find_dotenv(".env.local"), override=False)

# ============================================================
# Constants / configuration
# ============================================================

LOGGER_NAME = "odyss_ai_flows"
ENV_PREFIX = "ODYSS_FLOWS_"

DEFAULT_LOG_LEVEL = "DEBUG"
DEFAULT_MAX_LENGTH = 500

LOG_LEVEL = os.getenv(f"{ENV_PREFIX}LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
LOG_MAX_LENGTH = int(
    os.getenv(f"{ENV_PREFIX}LOG_MAX_LENGTH", DEFAULT_MAX_LENGTH)
)

# ============================================================
# ANSI color palette (presentation only)
# ============================================================

COLOR_CODES = {
    "DEBUG": "\033[94m",
    "INFO": "\033[92m",
    "WARNING": "\033[93m",
    "ERROR": "\033[91m",
    "CRITICAL": "\033[1;91m",
    "RESET": "\033[0m",
}

# ============================================================
# Filters (semantic shaping layer)
# ============================================================


class RunNameFilter(logging.Filter):
    """
    Injects run_name from contextvars into log record.
    Safe fallback if context is unavailable.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from odyss_ai_flows.core.runtime.run_context import get_run_name

            record.run_name = get_run_name()
        except Exception:
            record.run_name = None
        return True


class PathLabelFilter(logging.Filter):
    """
    Extracts last 2 parts of file path into record.path_label
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            path = Path(record.pathname).with_suffix("")
            record.path_label = "/".join(path.parts[-2:])
        except Exception:
            record.path_label = record.module
        return True


class TruncationFilter(logging.Filter):
    """
    Truncates long log messages.
    """

    def __init__(self, max_length: int, only_debug: bool = False):
        super().__init__()
        self.max_length = max_length
        self.only_debug = only_debug

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()

        if self.only_debug and record.levelname != "DEBUG":
            return True

        if self.max_length != -1 and len(msg) > self.max_length:
            msg = msg[: self.max_length] + "... [TRUNCATED]"

        record.msg = msg
        record.args = ()
        return True


class LabelComposerFilter(logging.Filter):
    """
    Composes final prefix:
    [run_name] [path/module] message
    """

    def filter(self, record: logging.LogRecord) -> bool:
        parts = []

        if getattr(record, "run_name", None):
            parts.append(f"[{record.run_name}]")

        if getattr(record, "path_label", None):
            parts.append(f"[{record.path_label}]")
        else:
            parts.append(f"[{record.module}]")

        prefix = " ".join(parts)

        # IMPORTANT: use original message again (not already prefixed)
        message = record.getMessage()

        record.msg = f"{prefix} {message}"
        record.args = ()

        return True


# ============================================================
# Formatter (presentation only)
# ============================================================


class ColoredFormatter(logging.Formatter):
    RESET = COLOR_CODES["RESET"]

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        level_color = COLOR_CODES.get(record.levelname, "")
        return f"{level_color}{base}{self.RESET}"


# ============================================================
# Logger instance (public API)
# ============================================================

logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(LOG_LEVEL)
logger.propagate = False

# ============================================================
# Handler helpers (explicit opt-in)
# ============================================================


def attach_handler(
    handler: logging.Handler,
    *,
    propagate: bool = True,
) -> None:
    logger.addHandler(handler)
    logger.propagate = propagate


def attach_colored_console_handler(
    *,
    level: Optional[int] = None,
    propagate: bool = True,
) -> None:
    stream = sys.stdout

    if getattr(stream, "encoding", None) != "utf-8":
        stream = io.TextIOWrapper(
            stream.buffer,
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )

    handler = logging.StreamHandler(stream)
    handler.setLevel(level or logging.DEBUG)
    handler.setFormatter(ColoredFormatter("%(message)s"))

    attach_handler(handler, propagate=propagate)


# ============================================================
# Filter pipeline setup (order matters!)
# ============================================================

logger.addFilter(RunNameFilter())
logger.addFilter(PathLabelFilter())
logger.addFilter(TruncationFilter(LOG_MAX_LENGTH))
logger.addFilter(LabelComposerFilter())

# ============================================================
# Import-time bootstrap (safe defaults)
# ============================================================

root = logging.getLogger()

if root.hasHandlers():
    logger.propagate = True
else:
    logger.propagate = False
    attach_colored_console_handler(propagate=False)
