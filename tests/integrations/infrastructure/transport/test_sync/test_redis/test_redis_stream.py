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
from pyddd.domain.message import (
    Message,
)
from pyddd.domain.abstractions import MessageType
from pyddd.infrastructure.transport.core.abstractions import (
    IMessageConsumer,
    IEventFactory,
)
from pyddd.infrastructure.transport.core.event_factory import (
    UniversalEventFactory,
    PublishedEventFactory,
)
from pyddd.infrastructure.transport.sync.domain import (
    DefaultAskPolicy,
    MessageConsumer,
    Notification,
    NotificationQueue,
)
from pyddd.infrastructure.transport.sync.redis.stream_group.consumer import (
    RedisStreamGroupConsumer,
)
from pyddd.infrastructure.transport.sync.redis.stream_group.publisher import (
    RedisStreamPublisher,
)


class TestStreamHandler:
    @pytest.fixture
    def handler(self, redis_stream_handler):
        return redis_stream_handler

    def test_reader_first_read_can_be_none(self, handler):
        handler.bind("user:update")
        messages = handler.read_batch()
        assert messages == []

    def test_reader_must_get_new_messages(self, handler, redis):
        payload = {"test_data": str(uuid.uuid4())}
        handler.bind("user:update")
        assert handler.read_batch() == []

        redis.xadd("user:update", payload)

        messages = handler.read_batch()
        message = messages.pop()
        assert isinstance(message, Notification)
        assert message.payload == payload

    def test_reader_could_read_ten_messages(self, redis, handler):
        handler.bind("user:update")
        assert handler.read_batch() == []

        [redis.xadd("user:update", {"test_data": str(uuid.uuid4())}) for _ in range(15)]

        messages = handler.read_batch(10)
        assert len(messages) == 10

    def test_reader_could_read_messages_from_all_topics(self, redis, handler):
        handler.bind('test:foo')
        handler.bind('test:bar')

        [redis.xadd("test:foo", {"test_data": str(uuid.uuid4())}) for _ in range(20)]
        [redis.xadd("test:bar", {"test_data": str(uuid.uuid4())}) for _ in range(20)]

        assert handler.read_batch() == []

        messages = handler.read_batch(10)
        assert len(messages) == 20


class TestConsumer:
    @pytest.fixture
    def handler(self, redis_stream_handler):
        return redis_stream_handler

    def test_message_consumer(self, redis, redis_stream_handler):
        module = Module("test")

        class ExampleCommand1(DomainCommand, domain="test"):
            bar: str

        class ExampleCommand2(DomainCommand, domain="test"):
            foo: str

        @module.subscribe("test.stream")
        @module.register
        def callback_1(cmd: ExampleCommand1, callback):
            return callback()

        @module.subscribe("test.stream")
        @module.register
        def callback_2(cmd: ExampleCommand2, callback):
            return callback()

        app = Application()
        app.include(module)

        callback = Mock()
        app.set_defaults("test", callback=callback)

        consumer = MessageConsumer(
            queue=NotificationQueue(message_handler=redis_stream_handler),
            ask_policy=DefaultAskPolicy(),
            event_factory=UniversalEventFactory(),
        )
        consumer.set_application(app)
        consumer.subscribe("test:stream")
        app.run()

        [redis.xadd("test:stream", {"foo": "true"}) for _ in range(5)]
        [redis.xadd("test:stream", {"bar": "true"}) for _ in range(5)]

        time.sleep(0.1)

        app.stop()

        assert callback.call_count == 10


class TestRedisStreamConsumer:
    def test_facade(self, redis):
        consumer = RedisStreamGroupConsumer(redis, group_name="test", consumer_name="consumer")
        assert isinstance(consumer, IMessageConsumer)
        assert isinstance(consumer.ask_policy, DefaultAskPolicy)
        assert isinstance(consumer.event_factory, PublishedEventFactory)
        assert isinstance(consumer.queue, NotificationQueue)

    def test_could_publish_event(self, redis):
        module = Module("test")

        class ExampleCommand(DomainCommand, domain="test"):
            bar: str

        @module.subscribe("test.stream")
        @module.register
        def callback_1(cmd: ExampleCommand, callback):
            return callback()

        callback = Mock()
        consumer = RedisStreamGroupConsumer(
            redis=redis,
            group_name=str(uuid.uuid4()),
            consumer_name=str(uuid.uuid4()),
            event_factory=UniversalEventFactory(),
        )
        app = Application()
        app.include(module)
        app.set_defaults(module.domain, callback=callback)
        consumer.set_application(app)
        consumer.subscribe("test:stream")
        app.run()

        [redis.xadd("test:stream", {"bar": "true"}) for _ in range(5)]

        time.sleep(0.1)

        app.stop()

        assert callback.call_count == 5


class TestPublisher:
    @pytest.fixture
    def app(self):
        app = Application()
        return app

    @pytest.fixture
    def get_publisher(self, app, redis):
        def _wrapper(event_factory: IEventFactory = None):
            publisher = RedisStreamPublisher(client=redis, event_factory=event_factory)
            publisher.set_application(app)
            return publisher

        return _wrapper

    def test_publish_event_universal_factory(self, redis, get_publisher, app):
        unique_name = str(uuid.uuid4())
        event = Message(
            message_type=MessageType.EVENT,
            full_name="test.domain.FakeEvent",
            payload={"test": "1"},
        )
        publisher = get_publisher(event_factory=UniversalEventFactory())
        publisher.register(event.__topic__)

        redis.xgroup_create(name=event.__topic__, groupname=unique_name, mkstream=True)
        app.run()
        app.handle(event)

        messages = redis.xreadgroup(
            groupname=unique_name,
            consumername=unique_name,
            streams={event.__topic__: ">"},
        )
        stream_name, streams = messages[0]
        message_id, payload = streams[0]
        assert {key.decode(): value.decode() for key, value in payload.items()} == event.to_dict()

    def test_publish_event_with_published_factory(self, redis, get_publisher, app):
        unique_name = str(uuid.uuid4())
        event = Message(
            message_type=MessageType.EVENT,
            full_name="test.domain.FakeEvent",
            payload={"test": True},
        )
        publisher = get_publisher()
        publisher.register(event.__topic__)

        redis.xgroup_create(name=event.__topic__, groupname=unique_name, mkstream=True)
        app.run()
        app.handle(event)

        messages = redis.xreadgroup(
            groupname=unique_name,
            consumername=unique_name,
            streams={event.__topic__: ">"},
        )
        stream_name, streams = messages[0]
        message_id, payload = streams[0]
        assert {key.decode(): value.decode() for key, value in payload.items()} == dict(
            full_event_name=event.__topic__,
            message_id=event.__message_id__,
            timestamp=str(event.__timestamp__.timestamp()),
            payload=event.to_json(),
        )
