import typing as t
from contextlib import suppress

from redis import ResponseError, Redis

from pyddd.infrastructure.transport.core.abstractions import (
    INotificationTrackerFactory,
    INotificationTracker,
    INotification,
)
from pyddd.infrastructure.transport.sync.domain import (
    Notification,
    IMessageHandler,
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

    def read(self, topic: str, limit: int = None) -> t.Sequence[INotification]:
        messages = []
        tracker = self._trackers[topic]
        response = self._read_message(topic, tracker.last_recent_notification_id, limit)
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

    def bind(self, topic: str):
        self._trackers[topic] = self._tracker_factory.create_tracker(topic)
        with suppress(ResponseError):
            self._client.xgroup_create(
                topic,
                self._group_name,
                mkstream=True
            )

    def _read_message(self, topic: str, last_message_id: str, limit: int = None) -> t.Union[list, t.Any]:
        return self._client.xreadgroup(
            self._group_name,
            self._consumer_name,
            {topic: last_message_id},
            count=limit,
            block=self._block,
        )

    def _ask(self, topic: str, message_id: str):

        def _wrapper(requeue: bool = False):
            if not requeue:
                self._client.xack(topic, self._group_name, message_id)

        return _wrapper
