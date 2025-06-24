import datetime
import json
import uuid

import pytest

from pyddd.domain.message import (
    Message,
)
from pyddd.domain.abstractions import IMessage
from pyddd.infrastructure.transport.core.abstractions import (
    IEventFactory,
    IPublishingMessage,
)
from pyddd.infrastructure.transport.core.event_factory import (
    UniversalEventFactory,
    PublishedEventFactory,
    UniversalPublishingMessage,
)
from pyddd.infrastructure.transport.core.value_objects import PublishedEvent


class TestUniversalEventFactory:
    @pytest.fixture
    def factory(self):
        return UniversalEventFactory()

    def test_must_impl_interface(self, factory):
        assert isinstance(factory, IEventFactory)

    def test_build_event(self, factory):
        notification = UniversalPublishingMessage(
            message_id=str(uuid.uuid4()),
            full_name="test:domain:FakeNotificationName",
            payload={"some_random": str(uuid.uuid4())},
        )
        message = factory.build_event(notification)
        assert isinstance(message, IMessage)
        assert message.__topic__ == "test.domain.FakeNotificationName"
        assert message.__type__ == "EVENT"
        assert message.__message_name__ == "FakeNotificationName"
        assert isinstance(message.__timestamp__, datetime.datetime)
        assert message.to_dict() == notification.payload

    def test_build_notification(self, factory):
        message = Message(
            message_type="EVENT",
            full_name="test.domain.FakeMessage",
            payload=dict(some_random=str(uuid.uuid4())),
        )
        notification = factory.build_publishing_message(message)
        assert isinstance(notification, IPublishingMessage)
        assert notification.name == "test.domain.FakeMessage"
        assert notification.payload == message.to_dict()


class TestPublishedEventDomainEventTranslator:
    @pytest.fixture
    def factory(self):
        return PublishedEventFactory()

    def test_must_impl_interface(self, factory):
        assert isinstance(factory, IEventFactory)

    def test_translate_from_notification(self, factory):
        published_event = PublishedEvent(
            full_event_name="test.domain.FakeNotificationName",
            message_id=str(uuid.uuid4()),
            payload=json.dumps(dict(result=True)),
            timestamp=str(datetime.datetime(2020, 1, 1, 1, 1, 25).timestamp()),
        )
        notification = UniversalPublishingMessage(
            message_id=str(uuid.uuid4()),
            full_name="test:domain:FakeNotificationName",
            payload=published_event.__dict__,
        )
        factory = PublishedEventFactory()
        message = factory.build_event(notification)
        assert isinstance(message, IMessage)
        assert message.__domain__ == "test.domain"
        assert message.__topic__ == "test.domain.FakeNotificationName"
        assert message.__message_name__ == "FakeNotificationName"
        assert message.__timestamp__ == datetime.datetime(2020, 1, 1, 1, 1, 25)
        assert message.to_dict() == dict(result=True)

    def test_build_notification(self, factory):
        event = Message(
            message_type="EVENT",
            full_name="test.domain.FakeEvent",
            payload={"some_random": str(uuid.uuid4())},
        )
        published_event = PublishedEvent(
            full_event_name=event.__topic__,
            message_id=event.__message_id__,
            payload=event.to_json(),
            timestamp=str(event.__timestamp__.timestamp()),
        )
        notification = factory.build_publishing_message(event)
        assert notification.name == event.__topic__
        assert notification.payload == published_event.__dict__
