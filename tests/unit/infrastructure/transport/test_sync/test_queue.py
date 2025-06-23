import time
import uuid
from unittest.mock import Mock

from pyddd.infrastructure.transport.sync.domain import (
    IMessageHandler,
    PublishedMessage,
    NotificationQueue,
)


class FakeHandler(IMessageHandler):
    def __init__(self, messages: list[PublishedMessage]):
        self._messages = iter(messages)

    def read(self, topic: str, limit: int = None) -> list[PublishedMessage]:
        return [message for message in self._messages if message.name == topic][:limit]

    def bind(self, topic: str):
        pass


class TestNotificationQueue:
    def test_consume_must_sent_message_to_callback(self):
        messages = [
            PublishedMessage(
                message_id=str(uuid.uuid4()),
                name="test:stream",
                payload={},
                ask_func=lambda: ...,
                reject_func=lambda x: ...,
            )
        ]
        reader = FakeHandler(messages)
        queue = NotificationQueue(message_handler=reader)
        queue.bind("test:stream")
        callback = Mock()
        queue.consume(callback)
        time.sleep(0.01)
        callback.assert_called_with(messages[0])
        queue.stop_consume()

    def test_queue_must_ignore_errors(self):
        message = PublishedMessage(
            message_id=str(uuid.uuid4()),
            name="test:stream",
            payload={},
        )
        reader = FakeHandler([message])
        queue = NotificationQueue(message_handler=reader)
        queue.bind("test:stream")
        callback = Mock(side_effect=[Exception(), message])
        queue.consume(callback)
        time.sleep(0.01)
        callback.assert_called_with(message)
        queue.stop_consume()

    def test_must_not_wait_callback(self):
        def endless_callback(*args, **kwargs):
            time.sleep(1000)

        messages = [
            PublishedMessage(
                message_id=str(uuid.uuid4()),
                name="test:stream",
                payload={},
            ),
            PublishedMessage(
                message_id=str(uuid.uuid4()),
                name="test:stream",
                payload={},
            ),
        ]
        reader = FakeHandler(messages)
        queue = NotificationQueue(message_handler=reader)
        queue.bind("test:stream")
        callback = Mock(side_effect=endless_callback)
        queue.consume(callback)
        time.sleep(0.01)
        callback.assert_called_with(messages[-1])
        queue.stop_consume()
