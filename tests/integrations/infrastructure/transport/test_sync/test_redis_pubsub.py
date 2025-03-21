import time
from unittest.mock import Mock

from pyddd.application import (
    Application,
    Module,
)
from pyddd.domain import DomainCommand
from pyddd.infrastructure.transport.asyncio.domain import DomainEventFactory
from pyddd.infrastructure.transport.sync.domain import (
    MessageConsumer,
    DefaultAskPolicy,
)
from pyddd.infrastructure.transport.sync.redis import PubSubNotificationQueue


class TestWithPubSub:
    def test_with_pubsub(self, redis):
        module = Module('test')

        class ExampleCommand1(DomainCommand, domain='test'):
            bar: str

        class ExampleCommand2(DomainCommand, domain='test'):
            foo: str

        @module.subscribe('another.stream')
        @module.subscribe('test.stream')
        @module.register
        def callback_1(cmd: ExampleCommand1, callback):
            return callback()

        @module.subscribe('test.stream')
        @module.register
        def callback_2(cmd: ExampleCommand2, callback):
            return callback()

        callback = Mock()
        consumer = MessageConsumer(
            queue=PubSubNotificationQueue(pubsub=redis.pubsub()),
            event_factory=DomainEventFactory(),
            ask_policy=DefaultAskPolicy()
        )
        app = Application()
        app.include(module)
        app.set_defaults(module.domain, callback=callback)
        consumer.set_application(app)
        consumer.subscribe('test:stream')
        consumer.subscribe('another:stream')
        app.run()

        [redis.publish("test:stream", '{"foo": "true"}') for _ in range(5)]
        [redis.publish("another:stream", '{"bar": "true"}') for _ in range(5)]
        [redis.publish("test:stream", '{"bar": "true"}') for _ in range(5)]

        time.sleep(0.1)

        app.stop()

        assert callback.call_count == 15
