import dataclasses
import typing as t
from contextlib import suppress

from redis import ResponseError
from redis.asyncio import Redis

from pyddd.application.abstractions import IApplication
from pyddd.infrastructure.transport.core.abstractions import (
    IMessageConsumer,
    IEventFactory,
    INotificationTrackerFactory,
    INotificationTracker,
    INotification,
    INotificationTrackerStrategy,
)
from pyddd.infrastructure.transport.core.event_factory import (
    PublishedEventFactory,
)
from pyddd.infrastructure.transport.core.tracker_factory import (
    NotificationTrackerFactory,
)
from pyddd.infrastructure.transport.asyncio.domain import (
    INotificationQueue,
    IAskPolicy,
    DefaultAskPolicy,
    NotificationQueue,
    MessageConsumer,
    IMessageHandler,
    Notification,
)
from pyddd.infrastructure.transport.core.value_objects import NotificationTrackerState


class RedisStreamGroupConsumer(IMessageConsumer):
    def __init__(
        self,
        redis: Redis,
        group_name: str,
        consumer_name: str,
        queue: INotificationQueue = None,
        event_factory: IEventFactory = None,
        ask_policy: IAskPolicy = None,
        block_ms: int = 0,
    ):
        self._ask_policy = ask_policy or DefaultAskPolicy()
        self._event_factory = event_factory or PublishedEventFactory()
        self._queue = queue or NotificationQueue(
            message_handler=GroupStreamHandler(
                group_name=group_name,
                consumer_name=consumer_name,
                client=redis,
                block=block_ms,
                tracker_factory=NotificationTrackerFactory(strategy=RedisStreamTrackerStrategy()),
            )
        )
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


class GroupStreamHandler(IMessageHandler):
    def __init__(
        self,
        group_name: str,
        consumer_name: str,
        client: Redis,
        tracker_factory: INotificationTrackerFactory,
        block: t.Optional[int] = 0,
    ):
        self._group_name = group_name
        self._consumer_name = consumer_name
        self._client = client
        self._block = block
        self._tracker_factory = tracker_factory
        self._trackers: dict[str, INotificationTracker] = {}

    async def read(self, topic: str, limit: int = None) -> t.Sequence[INotification]:
        messages = []
        tracker = self._trackers[topic]
        response = await self._read_message(topic, tracker.last_recent_notification_id, limit)
        for items in response:
            _, streams = items
            for stream in streams:
                message_id, payload = stream
                message = Notification(
                    message_id=message_id.decode(),
                    name=topic,
                    payload={key.decode(): value.decode() for key, value in payload.items()},
                    ask_func=self._ask(topic, message_id),
                    reject_func=self._ask(topic, message_id),
                )
                messages.append(message)
        tracker.track_messages(messages)
        return messages

    async def bind(self, topic: str):
        self._trackers[topic] = self._tracker_factory.create_tracker(topic)
        with suppress(ResponseError):
            await self._client.xgroup_create(topic, self._group_name, mkstream=True)

    async def _read_message(self, topic: str, last_message_id: str, limit: int = None) -> list:
        return await self._client.xreadgroup(
            self._group_name,
            self._consumer_name,
            {topic: last_message_id},
            count=limit,
            block=self._block,
        )

    def _ask(self, topic: str, message_id: str):
        async def _wrapper(requeue: bool = False):
            if not requeue:
                await self._client.xack(topic, self._group_name, message_id)

        return _wrapper


class RedisStreamTrackerStrategy(INotificationTrackerStrategy):
    def create_tracker(self, track_key: str) -> NotificationTrackerState:
        tracker = NotificationTrackerState(track_key=track_key, last_recent_notification_id="0")
        return tracker

    def track_most_recent_message(
        self, tracker: NotificationTrackerState, *messages: INotification
    ) -> NotificationTrackerState:
        if not messages:
            last_notification_id = ">"
        else:
            last_notification_id = messages[-1].message_id
        return dataclasses.replace(tracker, last_recent_notification_id=last_notification_id)
