from pyddd.domain.abstractions import (
    IDomainEventSubscriber,
    EventT,
)


class DomainEventPublisher:
    def __init__(self):
        self._subscribers: list[IDomainEventSubscriber] = []

    def subscribe(self, subscriber: IDomainEventSubscriber[EventT]):
        self._subscribers.append(subscriber)

    def publish(self, event: EventT):
        for subscriber in self._subscribers:
            if isinstance(event, subscriber.subscribed_to_type()):
                subscriber.handle(event)

    @property
    def subscribers(self):
        return self._subscribers
