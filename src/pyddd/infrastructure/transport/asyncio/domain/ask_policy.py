from pyddd.application import Application
from pyddd.infrastructure.transport.asyncio.domain.notification import Notification
from pyddd.infrastructure.transport.asyncio.domain.abstractions import (
    IAskPolicy,
    IEventFactory,
)


class DefaultAskPolicy(IAskPolicy):

    async def process(self, notification: Notification, event_factory: IEventFactory, application: Application):
        try:
            event = event_factory.build_event(notification)
            await application.handle(event)
            await notification.ack()
        except Exception as exc:
            # todo: log it!
            ...
