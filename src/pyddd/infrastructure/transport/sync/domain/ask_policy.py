from pyddd.application.abstractions import IApplication
from pyddd.infrastructure.transport.sync.domain.abstractions import (
    IAskPolicy,
    IEventFactory,
    INotification,
)


class DefaultAskPolicy(IAskPolicy):

    def process(self, notification: INotification, event_factory: IEventFactory, application: IApplication):
        try:
            event = event_factory.build_event(notification)
            application.handle(event)
            notification.ack()
        except Exception:
            # todo: log it!
            ...
