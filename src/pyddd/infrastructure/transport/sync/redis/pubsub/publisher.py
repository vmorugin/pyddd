import json
import logging

from redis import Redis
from pyddd.application.abstractions import (
    IApplication,
    ApplicationSignal,
)
from pyddd.domain.message import IMessage
from pyddd.infrastructure.transport.core.publisher import (
    EventPublisherModule,
)
from pyddd.infrastructure.transport.core.value_objects import PublishedEvent


class RedisPubSubPublisher:
    def __init__(self, client: Redis, logger_name: str = 'pyddd.event_publisher'):
        self._client = client
        self._module: EventPublisherModule = EventPublisherModule(self._publish)
        self._topics: set[str] = set()
        self._logger = logging.getLogger(logger_name)

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
        try:
            self._client.publish(
                channel=message.__topic__,
                message=json.dumps(
                    PublishedEvent(
                        full_event_name=message.__topic__,
                        message_id=message.__message_id__,
                        timestamp=str(message.__timestamp__.timestamp()),
                        payload=message.to_json()
                    ).__dict__  # type: ignore[arg-type]
                )
            )
        except Exception as exc:
            self._logger.critical(f"Failed to publish message {message.__topic__}", exc_info=exc)
