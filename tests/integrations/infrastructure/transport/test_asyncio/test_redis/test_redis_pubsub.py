import asyncio
import json
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
from pyddd.infrastructure.transport.asyncio.domain import (
    MessageConsumer,
    DefaultAskPolicy,
)
from pyddd.infrastructure.transport.asyncio.redis import PubSubNotificationQueue
from pyddd.infrastructure.transport.core.event_factory import UniversalEventFactory
from pyddd.infrastructure.transport.asyncio.redis.pubsub.publisher import RedisPubSubPublisher


class TestWithPubSub:
    async def test_with_pubsub(self, redis):
        module = Module('test')

        class ExampleCommand1(DomainCommand, domain='test'):
            bar: str

        class ExampleCommand2(DomainCommand, domain='test'):
            foo: str

        @module.subscribe('another.stream')
        @module.subscribe('test.stream')
        @module.register
        async def callback_1(cmd: ExampleCommand1, callback):
            return callback()

        @module.subscribe('test.stream')
        @module.register
        async def callback_2(cmd: ExampleCommand2, callback):
            return callback()

        callback = Mock()
        event_factory = UniversalEventFactory()
        queue = PubSubNotificationQueue(pubsub=redis.pubsub())
        consumer = MessageConsumer(
            queue=queue,
            event_factory=event_factory,
            ask_policy=DefaultAskPolicy()
        )
        app = Application()
        app.include(module)
        app.set_defaults(module.domain, callback=callback)
        consumer.set_application(app)
        consumer.subscribe('test:stream')
        consumer.subscribe('another:stream')
        await app.run_async()
        await asyncio.sleep(0.01)

        [await redis.publish("test:stream", '{"foo": "true"}') for _ in range(5)]
        [await redis.publish("another:stream", '{"bar": "true"}') for _ in range(5)]
        [await redis.publish("test:stream", '{"bar": "true"}') for _ in range(5)]

        await asyncio.sleep(0.01)
        assert callback.call_count == 15
        await app.stop_async()


class TestPublisher:
    async def test_publish_event(self, redis):
        event = Message(
            message_type=MessageType.EVENT,
            full_name='test.domain.FakeEvent',
            payload={'test': True},
        )
        app = Application()
        publisher = RedisPubSubPublisher(client=redis)
        publisher.set_application(app)
        publisher.register(event.__topic__)

        pubsub = redis.pubsub()
        await pubsub.subscribe(event.__topic__)

        await app.run_async()
        await app.handle(event)

        welcome_message = await pubsub.get_message()
        assert welcome_message is not None

        message = await pubsub.get_message(ignore_subscribe_messages=True)
        data = json.loads(message['data'])
        assert data == dict(
            full_event_name=event.__topic__,
            message_id=event.__message_id__,
            payload=event.to_json(),
            timestamp=str(event.__timestamp__.timestamp())
            )
