import asyncio
import uuid
from unittest.mock import AsyncMock

from pyddd.infrastructure.transport.asyncio.domain import (
    IMessageHandler,
    Notification,
    NotificationQueue,
)


class FakeHandler(IMessageHandler):
    def __init__(self, messages: list[Notification]):
        self._messages = messages

    async def read(self, topic: str, limit: int = None) -> list[Notification]:
        return self._messages

    async def bind(self, topic: str):
        pass


class TestNotificationQueue:

    async def test_consume_must_sent_message_to_callback(self):
        messages = [Notification(
            message_id=str(uuid.uuid4()),
            name='test:stream',
            payload={},
            ask_func=lambda: ...,
            reject_func=lambda x: ...
        )]
        reader = FakeHandler(messages)
        queue = NotificationQueue(message_handler=reader)
        await queue.bind('test:stream')
        callback = AsyncMock()
        await queue.consume(callback)
        await asyncio.sleep(0.01)
        callback.assert_called_with(messages[0])

    async def test_queue_must_ignore_errors(self):
        messages = [
            Exception(),
            Notification(
                message_id=str(uuid.uuid4()),
                name='test:stream',
                payload={},
            ),
        ]
        reader = FakeHandler(messages)
        queue = NotificationQueue(message_handler=reader)
        await queue.bind('test:stream')
        callback = AsyncMock(side_effect=[messages])
        await queue.consume(callback)
        await asyncio.sleep(0.01)
        callback.assert_called_with(messages[-1])

    async def test_must_not_wait_callback(self):
        async def endless_callback(*args, **kwargs):
            await asyncio.sleep(1000)

        messages = [
            Notification(
                message_id=str(uuid.uuid4()),
                name='test:stream',
                payload={},
            ),
            Notification(
                message_id=str(uuid.uuid4()),
                name='test:stream',
                payload={},
            ),
        ]
        reader = FakeHandler(messages)
        queue = NotificationQueue(message_handler=reader)
        await queue.bind('test:stream')
        callback = AsyncMock(side_effect=endless_callback)
        await queue.consume(callback)
        await asyncio.sleep(0.01)
        callback.assert_called_with(messages[-1])
