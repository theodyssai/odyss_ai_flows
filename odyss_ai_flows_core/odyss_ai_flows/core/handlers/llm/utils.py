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


class BufferedLogger(logging.Logger):
    def __init__(self, name: str, level=logging.NOTSET):
        super().__init__(name, level)
        self._log_buffer = []

    def handle(self, record: logging.LogRecord):
        self._log_buffer.append(record.getMessage())

    def get_buffered_logs(self):
        return self._log_buffer

    def clear_buffer(self):
        self._log_buffer.clear()
