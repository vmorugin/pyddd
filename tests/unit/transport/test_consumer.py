from unittest.mock import Mock

from pyddd.application import Application
from pyddd.application.abstractions import (
    IApplication,
)

from pyddd.infrastructure.transport.asyncio.domain import (
    MessageConsumer,
    INotificationQueue,
)


class TestConsumer:
    async def test_should_bind_queue_to_topic_when_subscribe(self):
        consumer = MessageConsumer(
            queue=...,
            ask_policy=...,
            event_factory=...
        )
        consumer.subscribe('example-stream:test')
        assert consumer.subscriptions == {'example-stream:test'}

    async def test_should_set_application(self):
        app = Mock(spec=IApplication)
        consumer = MessageConsumer(
            queue=...,
            ask_policy=...,
            event_factory=...
        )
        consumer.set_application(application=app)

    async def test_should_bind_queue_and_start_consume_when_run_app(self):
        queue = Mock(spec=INotificationQueue)
        app = Application()
        consumer = MessageConsumer(
            queue=queue,
            ask_policy=...,
            event_factory=...
        )
        consumer.subscribe('example:event')
        consumer.set_application(application=app)
        await app.run_async()
        queue.bind.assert_called_with('example:event')
        queue.consume.assert_called_with(consumer._ask_message)

    async def test_should_stop_consume_when_stop_app(self):
        queue = Mock(spec=INotificationQueue)
        app = Application()
        consumer = MessageConsumer(
            queue=queue,
            ask_policy=...,
            event_factory=...
        )
        consumer.subscribe('example:event')
        consumer.set_application(application=app)
        await app.run_async()
        await app.stop_async()
        queue.stop_consume.assert_called()
