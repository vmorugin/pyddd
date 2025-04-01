from pyddd.application.abstractions import IApplication
from pyddd.infrastructure.transport.asyncio.domain.abstractions import (
    IAskPolicy,
    IEventFactory,
    INotification,
)


class DefaultAskPolicy(IAskPolicy):

    async def process(self, notification: INotification, event_factory: IEventFactory, application: IApplication):
        try:
            event = event_factory.build_event(notification)
            await application.handle(event)
            await notification.ack()
        except Exception:
            # todo: log it!
            ...
