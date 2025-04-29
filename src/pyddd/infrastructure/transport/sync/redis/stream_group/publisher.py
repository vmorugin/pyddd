import logging

from redis import Redis
from pyddd.application.abstractions import (
    IApplication,
    ApplicationSignal,
)
from pyddd.domain.abstractions import IMessage
from pyddd.infrastructure.transport.core.abstractions import IEventFactory
from pyddd.infrastructure.transport.core.event_factory import (
    PublishedEventFactory,
    UniversalEventFactory,
)
from pyddd.infrastructure.transport.core.publisher import (
    EventPublisherModule,
)


class RedisStreamPublisher:
    def __init__(
        self,
        client: Redis,
        event_factory: IEventFactory = None,
        logger_name: str = "pyddd.event_publisher",
    ):
        logger = logging.getLogger(logger_name)
        if isinstance(event_factory, UniversalEventFactory):
            logger.warning(
                "Be careful using UniversalEventFactory with RedisStreams!\n"
                "The factory won't wrapp your payload and could raise an error "
                "if a message include custom keys or value (nor str, int, bytes)"
            )
        self._client = client
        self._module: EventPublisherModule = EventPublisherModule(self._publish)
        self._event_factory = event_factory or PublishedEventFactory()
        self._topics: set[str] = set()
        self._logger = logger

    def set_application(self, application: IApplication):
        application = application

        application.subscribe(ApplicationSignal.BEFORE_RUN, self._before_run)

    def register(self, event_topic: str):
        self._topics.add(event_topic)

    def _before_run(self, signal: ApplicationSignal, app: IApplication):
        for topic in self._topics:
            self._module.register(topic)

        app.include(self._module)

    def _publish(self, message: IMessage):
        notification = self._event_factory.build_notification(message)
        try:
            self._client.xadd(name=message.__topic__, fields=notification.payload)
        except Exception as exc:
            self._logger.critical(f"Failed to publish message {message.__topic__}", exc_info=exc)
