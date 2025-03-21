import asyncio
import uuid
from unittest.mock import (
    Mock,
)

import pytest

from pyddd.application import (
    Application,
    AsyncExecutor,
    Module,
)
from pyddd.domain import DomainCommand

from pyddd.infrastructure.transport.asyncio.domain import (
    DefaultAskPolicy,
    MessageConsumer,
    Notification,
    NotificationQueue,
)
from pyddd.infrastructure.transport.core.event_factory import DomainEventFactory


class TestStreamHandler:
    @pytest.fixture
    def handler(self, redis_stream_handler):
        return redis_stream_handler

    async def test_reader_first_read_can_be_none(self, handler):
        await handler.bind('user:update')
        messages = await handler.read('user:update')
        assert messages == []

    async def test_reader_must_get_new_messages(self, handler, redis):
        payload = {'test_data': str(uuid.uuid4())}
        await handler.bind('user:update')
        assert await handler.read(topic='user:update') == []

        await redis.xadd('user:update', payload)

        messages = await handler.read(topic='user:update')
        message = messages.pop()
        assert isinstance(message, Notification)
        assert message.payload == payload

    async def test_reader_could_read_ten_messages(self, redis, handler):
        await handler.bind('user:update')
        assert await handler.read('user:update') == []

        [await redis.xadd('user:update', {'test_data': str(uuid.uuid4())}) for _ in range(10)]

        messages = await handler.read('user:update')
        assert len(messages) >= 10


class TestConsumer:
    @pytest.fixture
    def handler(self, redis_stream_handler):
        return redis_stream_handler

    async def test_message_consumer(self, redis, redis_stream_handler):
        module = Module('test')

        class ExampleCommand1(DomainCommand, domain='test'):
            bar: str

        class ExampleCommand2(DomainCommand, domain='test'):
            foo: str

        @module.subscribe('test.stream')
        @module.register
        async def callback_1(cmd: ExampleCommand1, callback):
            return callback()

        @module.subscribe('test.stream')
        @module.register
        async def callback_2(cmd: ExampleCommand2, callback):
            return callback()

        app = Application(executor=AsyncExecutor())
        app.include(module)

        callback = Mock()
        app.set_defaults('test', callback=callback)

        ask_policy = DefaultAskPolicy()
        queue = NotificationQueue(message_handler=redis_stream_handler)
        consumer = MessageConsumer(queue=queue, ask_policy=ask_policy, event_factory=DomainEventFactory())
        consumer.set_application(app)
        consumer.subscribe('test:stream')
        await app.run_async()

        [await redis.xadd("test:stream", {'foo': 'true'}) for _ in range(5)]
        [await redis.xadd("test:stream", {'bar': 'true'}) for _ in range(5)]

        await asyncio.sleep(0.1)
        await app.stop_async()

        assert callback.call_count == 10
