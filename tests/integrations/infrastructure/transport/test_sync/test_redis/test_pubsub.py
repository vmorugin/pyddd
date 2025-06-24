import json
import time
from time import sleep
from unittest.mock import Mock

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
    MessageConsumer,
    DefaultAskPolicy,
)
from pyddd.infrastructure.transport.sync.redis.pubsub.consumer import (
    RedisPubSubConsumer,
    PubSubNotificationQueue,
)
from pyddd.infrastructure.transport.sync.redis.pubsub.publisher import (
    RedisPubSubPublisher,
)


class TestWithPubSub:
    def test_with_pubsub(self, redis):
        module = Module("test")

        class ExampleCommand1(DomainCommand, domain="test"):
            bar: str

        class ExampleCommand2(DomainCommand, domain="test"):
            foo: str

        @module.subscribe("another.stream")
        @module.subscribe("test.stream")
        @module.register
        def callback_1(cmd: ExampleCommand1, callback):
            return callback()

        @module.subscribe("test.stream")
        @module.register
        def callback_2(cmd: ExampleCommand2, callback):
            return callback()

        callback = Mock()
        consumer = MessageConsumer(
            queue=PubSubNotificationQueue(pubsub=redis.pubsub()),
            event_factory=UniversalEventFactory(),
            ask_policy=DefaultAskPolicy(),
        )
        app = Application()
        app.include(module)
        app.set_defaults(module.domain, callback=callback)
        consumer.set_application(app)
        consumer.subscribe("test:stream")
        consumer.subscribe("another:stream")
        app.run()

        [redis.publish("test:stream", '{"foo": "true"}') for _ in range(5)]
        [redis.publish("another:stream", '{"bar": "true"}') for _ in range(5)]
        [redis.publish("test:stream", '{"bar": "true"}') for _ in range(5)]

        time.sleep(0.1)

        app.stop()

        assert callback.call_count == 15


class TestRedisPubsubConsumer:
    def test_facade(self, redis):
        consumer = RedisPubSubConsumer(redis)
        assert isinstance(consumer, IMessageConsumer)
        assert isinstance(consumer.ask_policy, DefaultAskPolicy)
        assert isinstance(consumer.event_factory, UniversalEventFactory)
        assert isinstance(consumer.queue, PubSubNotificationQueue)

    def test_could_publish_event(self, redis):
        module = Module("test")

        class ExampleCommand(DomainCommand, domain="test"):
            bar: str

        @module.subscribe("test.stream")
        @module.register
        def callback_1(cmd: ExampleCommand, callback):
            return callback()

        callback = Mock()
        consumer = RedisPubSubConsumer(redis, event_factory=UniversalEventFactory())
        app = Application()
        app.include(module)
        app.set_defaults(module.domain, callback=callback)
        consumer.set_application(app)
        consumer.subscribe("test:stream")
        app.run()

        [redis.publish("test:stream", '{"bar": "true"}') for _ in range(5)]

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
            publisher = RedisPubSubPublisher(client=redis, event_factory=event_factory)
            publisher.set_application(app)
            return publisher

        return _wrapper

    def test_publish_with_universal_factory(self, redis, get_publisher, app):
        event = Message(
            message_type=MessageType.EVENT,
            full_name="test.domain.FakeEvent",
            payload={"test": True},
        )
        publisher = get_publisher()
        publisher.register(event.__topic__)

        pubsub = redis.pubsub()
        pubsub.subscribe(event.__topic__)

        app.run()
        list(app.handle(event))

        welcome_message = pubsub.get_message()
        assert welcome_message is not None

        sleep(0.1)
        message = pubsub.get_message()
        data = json.loads(message["data"])
        assert data == event.to_dict()

    def test_publish_event_with_published_event_factory(self, redis, get_publisher, app):
        event = Message(
            message_type=MessageType.EVENT,
            full_name="test.domain.FakeEvent",
            payload={"test": True},
        )
        publisher = get_publisher(event_factory=PublishedEventFactory())
        publisher.register(event.__topic__)

        pubsub = redis.pubsub()
        pubsub.subscribe(event.__topic__)

        app.run()
        list(app.handle(event))

        welcome_message = pubsub.get_message()
        assert welcome_message is not None

        time.sleep(0.01)

        message = pubsub.get_message()
        data = json.loads(message["data"])
        assert data == dict(
            full_event_name=event.__topic__,
            message_id=event.__message_id__,
            payload=event.to_json(),
            timestamp=str(event.__timestamp__.timestamp()),
        )
