import asyncio
from odyss_ai_flows.core.utils.logger import logger


class HealableAsyncResource:
    def __init__(self, resource_factory, max_retries=1):
        self._factory = resource_factory
        self._resource = None
        self._epoch = 0
        self._lock = asyncio.Lock()
        self._max_retries = max_retries

        logger.debug(
            "[HAR:init] max_retries=%s",
            max_retries,
        )

    def __getattr__(self, name):
        async def method(*args, **kwargs):
            async def op(resource):
                return await getattr(resource, name)(*args, **kwargs)

            return await self.run(op)

        return method

    async def run(self, op):
        attempts = 0

        while True:
            async with self._lock:
                if self._resource is None:
                    logger.info(
                        "[HAR:create] creating resource (next_epoch=%s)",
                        self._epoch + 1,
                    )
                    self._resource = await self._factory()

                resource = self._resource
                epoch = self._epoch

            try:
                return await op(resource)

            except Exception:
                attempts += 1

                logger.warning(
                    "[HAR:error] epoch=%s attempt=%s/%s",
                    epoch,
                    attempts,
                    self._max_retries,
                    exc_info=True,
                )

                if attempts > self._max_retries:
                    logger.error(
                        "[HAR:giveup] epoch=%s attempts=%s",
                        epoch,
                        attempts,
                    )
                    raise

                async with self._lock:
                    if self._epoch != epoch:
                        logger.debug(
                            "[HAR:heal:skip] intent_epoch=%s current_epoch=%s",
                            epoch,
                            self._epoch,
                        )
                        continue

                    logger.info(
                        "[HAR:heal] closing and recreating resource (epoch=%s)",
                        epoch,
                    )

                    try:
                        await self._resource.close()
                    except Exception:
                        logger.exception(
                            "[HAR:heal] error while closing resource (epoch=%s)",
                            epoch,
                        )

                    self._resource = None
                    self._epoch += 1

                    logger.info(
                        "[HAR:heal] advanced to epoch=%s",
                        self._epoch,
                    )
