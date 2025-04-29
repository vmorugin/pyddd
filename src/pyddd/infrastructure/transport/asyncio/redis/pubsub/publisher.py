import json
import logging

from redis.asyncio import Redis
from pyddd.application.abstractions import (
    IApplication,
    ApplicationSignal,
)
from pyddd.domain.abstractions import IMessage
from pyddd.infrastructure.transport.core.abstractions import IEventFactory
from pyddd.infrastructure.transport.core.event_factory import UniversalEventFactory
from pyddd.infrastructure.transport.core.publisher import (
    EventPublisherModule,
)


class RedisPubSubPublisher:
    def __init__(
        self,
        client: Redis,
        event_factory: IEventFactory = None,
        logger_name: str = "pyddd.event_publisher",
    ):
        self._client = client
        self._module: EventPublisherModule = EventPublisherModule(self._publish)
        self._event_factory = event_factory or UniversalEventFactory()
        self._topics: set[str] = set()
        self._logger = logging.getLogger(logger_name)

    def set_application(self, application: IApplication):
        application = application

        application.subscribe(ApplicationSignal.BEFORE_RUN, self._before_run)

    def register(self, event_topic: str):
        self._topics.add(event_topic)

    async def _before_run(self, signal: ApplicationSignal, app: IApplication):
        for topic in self._topics:
            self._module.register(topic)

        app.include(self._module)

    async def _publish(self, message: IMessage):
        notification = self._event_factory.build_notification(message)
        try:
            await self._client.publish(
                channel=message.__topic__,
                message=json.dumps(notification.payload),
            )
        except Exception as exc:
            self._logger.critical(f"Failed to publish message {message.__topic__}", exc_info=exc)
