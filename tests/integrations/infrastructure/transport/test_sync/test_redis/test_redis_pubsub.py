import json
import time
from unittest.mock import Mock

from pyddd.application import (
    Application,
    Module,
)
from pyddd.domain import DomainCommand
from pyddd.domain.message import (
    Message,
    MessageType,
)
from pyddd.infrastructure.transport.core.abstractions import (
    IMessageConsumer,
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
        assert isinstance(consumer.event_factory, PublishedEventFactory)
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
    def test_publish_event(self, redis):
        event = Message(
            message_type=MessageType.EVENT,
            full_name="test.domain.FakeEvent",
            payload={"test": True},
        )
        app = Application()
        publisher = RedisPubSubPublisher(client=redis)
        publisher.set_application(app)
        publisher.register(event.__topic__)

        pubsub = redis.pubsub()
        pubsub.subscribe(event.__topic__)

        app.run()
        list(app.handle(event))

        welcome_message = pubsub.get_message()
        assert welcome_message is not None

        message = pubsub.get_message(ignore_subscribe_messages=True)
        data = json.loads(message["data"])
        assert data == dict(
            full_event_name=event.__topic__,
            message_id=event.__message_id__,
            payload=event.to_json(),
            timestamp=str(event.__timestamp__.timestamp()),
        )
