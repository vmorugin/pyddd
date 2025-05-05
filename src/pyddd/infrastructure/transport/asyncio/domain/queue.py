import asyncio
import logging

from pyddd.infrastructure.transport.asyncio.domain.abstractions import (
    INotificationQueue,
    IMessageHandler,
    ICallback,
)


class NotificationQueue(INotificationQueue):
    def __init__(
        self,
        message_handler: IMessageHandler,
        *,
        batch_size: int = 50,
        delay_ms: int = 10,
        logger_name: str = "pyddd.transport.queue",
    ):
        self._handler = message_handler
        self._topics: set[str] = set()
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._batch_size = batch_size
        self._delay_ms = delay_ms * 0.001
        self._logger = logging.getLogger(logger_name)

    async def bind(self, topic: str):
        self._topics.add(topic)
        await self._handler.bind(topic)

    async def consume(self, callback: ICallback):
        self._running = True
        for topic in self._topics:
            task = asyncio.create_task(self._long_pull(topic, callback))
            self._tasks.append(task)

    async def stop_consume(self):
        self._running = False
        for task in self._tasks:
            task.cancel(f"Canceled task {task}")

    async def _long_pull(self, topic: str, callback: ICallback):
        while self._running:
            try:
                messages = await self._handler.read(topic, limit=self._batch_size)
                for message in messages:
                    asyncio.create_task(callback(message))
            except Exception as exc:
                self._logger.error(f"Unexpected error while pulling {topic} messages!", exc_info=exc)
            await asyncio.sleep(self._delay_ms)
