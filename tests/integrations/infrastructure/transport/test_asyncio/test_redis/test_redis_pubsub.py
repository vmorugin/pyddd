import asyncio
import json
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
from pyddd.infrastructure.transport.asyncio.domain import (
    MessageConsumer,
    DefaultAskPolicy,
)
from pyddd.infrastructure.transport.asyncio.redis.pubsub.consumer import (
    RedisPubSubConsumer,
    PubSubNotificationQueue,
)
from pyddd.infrastructure.transport.core.abstractions import (
    IMessageConsumer,
    IEventFactory,
)
from pyddd.infrastructure.transport.core.event_factory import (
    UniversalEventFactory,
    PublishedEventFactory,
)
from pyddd.infrastructure.transport.asyncio.redis.pubsub.publisher import (
    RedisPubSubPublisher,
)


class TestWithPubSub:
    async def test_with_pubsub(self, redis):
        module = Module("test")

        class ExampleCommand1(DomainCommand, domain="test"):
            bar: str

        class ExampleCommand2(DomainCommand, domain="test"):
            foo: str

        @module.subscribe("another.stream")
        @module.subscribe("test.stream")
        @module.register
        async def callback_1(cmd: ExampleCommand1, callback):
            return callback()

        @module.subscribe("test.stream")
        @module.register
        async def callback_2(cmd: ExampleCommand2, callback):
            return callback()

        callback = Mock()
        event_factory = UniversalEventFactory()
        queue = PubSubNotificationQueue(pubsub=redis.pubsub())
        consumer = MessageConsumer(queue=queue, event_factory=event_factory, ask_policy=DefaultAskPolicy())
        app = Application()
        app.include(module)
        app.set_defaults(module.domain, callback=callback)
        consumer.set_application(app)
        consumer.subscribe("test:stream")
        consumer.subscribe("another:stream")
        await app.run_async()
        await asyncio.sleep(0.01)

        [await redis.publish("test:stream", '{"foo": "true"}') for _ in range(5)]
        [await redis.publish("another:stream", '{"bar": "true"}') for _ in range(5)]
        [await redis.publish("test:stream", '{"bar": "true"}') for _ in range(5)]

        await asyncio.sleep(0.01)
        assert callback.call_count == 15
        await app.stop_async()


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

    async def test_publish_with_universal_factory(self, redis, get_publisher, app):
        event = Message(
            message_type=MessageType.EVENT,
            full_name="test.domain.FakeEvent",
            payload={"test": "1"},
        )
        publisher = get_publisher()
        publisher.register(event.__topic__)

        pubsub = redis.pubsub()
        await pubsub.subscribe(event.__topic__)

        await app.run_async()
        list(await app.handle(event))

        welcome_message = await pubsub.get_message()
        assert welcome_message is not None

        message = await pubsub.get_message(ignore_subscribe_messages=True)
        await asyncio.sleep(0.1)
        data = json.loads(message["data"])
        assert data == event.to_dict()

    async def test_publish_event_with_published_event_factory(self, redis, get_publisher, app):
        event = Message(
            message_type=MessageType.EVENT,
            full_name="test.domain.FakeEvent",
            payload={"test": True},
        )
        publisher = get_publisher(event_factory=PublishedEventFactory())
        publisher.register(event.__topic__)

        pubsub = redis.pubsub()
        await pubsub.subscribe(event.__topic__)

        await app.run_async()
        list(await app.handle(event))

        welcome_message = await pubsub.get_message()
        assert welcome_message is not None

        message = await pubsub.get_message()
        data = json.loads(message["data"])
        assert data == dict(
            full_event_name=event.__topic__,
            message_id=event.__message_id__,
            payload=event.to_json(),
            timestamp=str(event.__timestamp__.timestamp()),
        )


class TestRedisPubsubConsumer:
    def test_facade(self, redis):
        consumer = RedisPubSubConsumer(redis)
        assert isinstance(consumer, IMessageConsumer)
        assert isinstance(consumer.ask_policy, DefaultAskPolicy)
        assert isinstance(consumer.event_factory, UniversalEventFactory)
        assert isinstance(consumer.queue, PubSubNotificationQueue)

    async def test_could_publish_event(self, redis):
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
        await app.run_async()

        [await redis.publish("test:stream", '{"bar": "true"}') for _ in range(5)]

        await asyncio.sleep(0.1)

        await app.stop_async()

        assert callback.call_count == 5
