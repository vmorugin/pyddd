import logging

from pyddd.application.abstractions import IApplication
from pyddd.infrastructure.transport.sync.domain.abstractions import (
    IAskPolicy,
    IEventFactory,
    IPublishedMessage,
)


class DefaultAskPolicy(IAskPolicy):
    def __init__(self, logger_name: str = "pyddd.transport.ask_policy"):
        self._logger = logging.getLogger(logger_name)

    def process(
        self,
        notification: IPublishedMessage,
        event_factory: IEventFactory,
        application: IApplication,
    ):
        try:
            event = event_factory.build_event(notification)
        except Exception as e:
            self._logger.critical(
                "Fail build event from message %s by reason: %s(%s)",
                notification,
                e.__class__.__name__,
                e,
                exc_info=e,
            )
            notification.reject(requeue=False)
            return

        try:
            results = application.handle(event)
            if len(results) == 0:
                self._logger.warning("Rejecting message %s by reason: %s", event, "Not handled")
                notification.reject(requeue=False)
            elif all((isinstance(result, Exception) for result in results)):
                self._logger.exception(
                    "Requeue message %s by reason: %s",
                    event,
                    "All handlers finished with exception",
                )
                notification.reject(requeue=True)
            else:
                notification.ack()
        except Exception as exc:
            self._logger.error(f"Error when handling notification {event}", exc_info=exc)
