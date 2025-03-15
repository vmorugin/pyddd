import typing as t
import asyncio
import json
import logging
import uuid

from redis.asyncio.client import PubSub

from pyddd.infrastructure.transport.asyncio.domain import (
    INotificationQueue,
    ICallback,
    Notification,
)


class PubSubNotificationQueue(INotificationQueue):
    def __init__(self, pubsub: PubSub, logger_name: str = 'notification.queue'):
        self._pubsub = pubsub
        self._running = False
        self._pooling_task: t.Optional[asyncio.Task] = None
        self._logger = logging.getLogger(logger_name)

    async def bind(self, topic: str):
        await self._pubsub.subscribe(topic)

    async def consume(self, callback: ICallback):
        self._running = True
        task = asyncio.create_task(self._long_pull(callback))
        self._pooling_task = task

    async def stop_consume(self):
        self._running = False
        await self._pubsub.unsubscribe()
        if self._pooling_task:
            self._pooling_task.cancel(f"Canceled task {self._pooling_task}")

    async def _long_pull(self, callback: ICallback):
        while self._running:
            try:
                async for message in self._pubsub.listen():
                    if message['type'] == 'message':
                        notification = Notification(
                            message_id=str(uuid.uuid4()),
                            name=message['channel'].decode(),
                            payload=json.loads(message['data']),
                        )
                        await callback(notification)
            except Exception as exc:
                self._logger.error("Unexpected error while pulling pubsub", exc_info=exc)
            await asyncio.sleep(0.001)
