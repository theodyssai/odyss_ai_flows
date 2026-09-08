from __future__ import annotations


class OrchestrationError(Exception):

    def __init__(
        self,
        message: str,
        *,
        instance_id: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)

        self.instance_id = instance_id
        self.cause = cause
