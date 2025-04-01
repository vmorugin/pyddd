import typing as t
from contextlib import suppress

from redis import ResponseError
from redis.asyncio import Redis

from pyddd.infrastructure.transport.asyncio.domain import (
    IMessageHandler,
)
from pyddd.infrastructure.transport.asyncio.domain import Notification
from pyddd.infrastructure.transport.core.abstractions import (
    INotificationTrackerFactory,
    INotificationTracker,
    INotification,
)


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
            await self._client.xgroup_create(
                topic,
                self._group_name,
                mkstream=True
            )

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
