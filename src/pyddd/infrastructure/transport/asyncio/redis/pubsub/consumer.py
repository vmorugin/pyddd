import asyncio
import json
import logging
import typing as t
import uuid

from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from pyddd.application.abstractions import IApplication
from pyddd.infrastructure.transport.core.abstractions import (
    IMessageConsumer,
    IEventFactory,
)
from pyddd.infrastructure.transport.core.event_factory import UniversalEventFactory
from pyddd.infrastructure.transport.asyncio.domain import (
    INotificationQueue,
    IAskPolicy,
    DefaultAskPolicy,
    MessageConsumer,
    ICallback,
    PublishedMessage,
)


class RedisPubSubConsumer(IMessageConsumer):
    def __init__(
        self,
        redis: Redis,
        queue: INotificationQueue = None,
        event_factory: IEventFactory = None,
        ask_policy: IAskPolicy = None,
    ):
        self._ask_policy = ask_policy or DefaultAskPolicy()
        self._event_factory = event_factory or UniversalEventFactory()
        self._queue = queue or PubSubNotificationQueue(pubsub=redis.pubsub())
        self._consumer = MessageConsumer(
            queue=self._queue,
            event_factory=self._event_factory,
            ask_policy=self._ask_policy,
        )

    def subscribe(self, topic: str):
        return self._consumer.subscribe(topic)

    def set_application(self, application: IApplication):
        return self._consumer.set_application(application)

    @property
    def ask_policy(self):
        return self._ask_policy

    @property
    def event_factory(self):
        return self._event_factory

    @property
    def queue(self):
        return self._queue


class PubSubNotificationQueue(INotificationQueue):
    def __init__(self, pubsub: PubSub, logger_name: str = "pyddd.transport.queue"):
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
                    if message["type"] == "message":
                        notification = PublishedMessage(
                            message_id=str(uuid.uuid4()),
                            name=message["channel"].decode(),
                            payload=json.loads(message["data"]),
                        )
                        await callback(notification)
            except Exception as exc:
                self._logger.error("Unexpected error while pulling pubsub", exc_info=exc)
            await asyncio.sleep(0.001)
