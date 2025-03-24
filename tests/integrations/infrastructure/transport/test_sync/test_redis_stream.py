import time
import uuid
from unittest.mock import (
    Mock,
)

import pytest

from pyddd.application import (
    Application,
    Module,
)
from pyddd.domain import DomainCommand
from pyddd.infrastructure.transport.core.event_factory import UniversalEventFactory
from pyddd.infrastructure.transport.sync.domain import (
    DefaultAskPolicy,
    MessageConsumer,
    Notification,
    NotificationQueue,
)


class TestStreamHandler:
    @pytest.fixture
    def handler(self, redis_stream_handler):
        return redis_stream_handler

    def test_reader_first_read_can_be_none(self, handler):
        handler.bind('user:update')
        messages = handler.read('user:update')
        assert messages == []

    def test_reader_must_get_new_messages(self, handler, redis):
        payload = {'test_data': str(uuid.uuid4())}
        handler.bind('user:update')
        assert handler.read(topic='user:update') == []

        redis.xadd('user:update', payload)

        messages = handler.read(topic='user:update')
        message = messages.pop()
        assert isinstance(message, Notification)
        assert message.payload == payload

    def test_reader_could_read_ten_messages(self, redis, handler):
        handler.bind('user:update')
        assert handler.read('user:update') == []

        [redis.xadd('user:update', {'test_data': str(uuid.uuid4())}) for _ in range(10)]

        messages = handler.read('user:update')
        assert len(messages) >= 10


class TestConsumer:
    @pytest.fixture
    def handler(self, redis_stream_handler):
        return redis_stream_handler

    def test_message_consumer(self, redis, redis_stream_handler):
        module = Module('test')

        class ExampleCommand1(DomainCommand, domain='test'):
            bar: str

        class ExampleCommand2(DomainCommand, domain='test'):
            foo: str

        @module.subscribe('test.stream')
        @module.register
        def callback_1(cmd: ExampleCommand1, callback):
            return callback()

        @module.subscribe('test.stream')
        @module.register
        def callback_2(cmd: ExampleCommand2, callback):
            return callback()

        app = Application()
        app.include(module)

        callback = Mock()
        app.set_defaults('test', callback=callback)

        consumer = MessageConsumer(
            queue=NotificationQueue(message_handler=redis_stream_handler),
            ask_policy=DefaultAskPolicy(),
            event_factory=UniversalEventFactory()
            )
        consumer.set_application(app)
        consumer.subscribe('test:stream')
        app.run()

        [redis.xadd("test:stream", {'foo': 'true'}) for _ in range(5)]
        [redis.xadd("test:stream", {'bar': 'true'}) for _ in range(5)]

        time.sleep(0.1)

        app.stop()

        assert callback.call_count == 10
