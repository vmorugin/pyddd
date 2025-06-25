from unittest.mock import Mock

import pytest

from pyddd.domain import DomainEvent
from pyddd.domain.abstractions import (
    MessageType,
    EventT,
    IDomainEventSubscriber,
)
from pyddd.domain.message import Message
from pyddd.domain.publisher import DomainEventPublisher


class FakeEvent(DomainEvent, domain="test"): ...


class FakeDomainEventSubscriber(IDomainEventSubscriber[DomainEvent]):
    def __init__(self, callback: Mock):
        self._callback = callback

    def handle(self, event: EventT):
        self._callback(event)

    def subscribed_to_type(self) -> type[EventT]:
        return DomainEvent


@pytest.fixture
def callback():
    return Mock()


@pytest.fixture
def subscriber(callback):
    return FakeDomainEventSubscriber(callback)


class TestDomainEventSubscriber:
    def test_must_impl(self, subscriber):
        assert isinstance(subscriber, IDomainEventSubscriber)

    def test_could_get_subscribed_type(self, subscriber):
        assert subscriber.subscribed_to_type() == DomainEvent

    def test_could_handle(self, subscriber, callback):
        event = FakeEvent()
        subscriber.handle(event)
        callback.assert_called_with(event)


class TestDomainEventPublisher:
    @pytest.fixture
    def publisher(self):
        return DomainEventPublisher()

    def test_could_subscribe(self, subscriber, publisher):
        publisher.subscribe(subscriber)
        assert publisher.subscribers == [subscriber]

    def test_could_publish(self, subscriber, publisher, callback):
        publisher.subscribe(subscriber)
        event = FakeEvent()
        publisher.publish(event)
        callback.assert_called_with(event)

    def test_could_not_publish_if_event_not_subscribed_in_subscriber(self, subscriber, publisher, callback):
        publisher.subscribe(subscriber)
        event = Message(message_type=MessageType.EVENT, full_name="test.Message", payload={})
        publisher.publish(event)
        callback.assert_not_called()
