import datetime
import json
import uuid

from pyddd.infrastructure.transport.core.abstractions import (
    INotification,
    IEventFactory,
)
from pyddd.infrastructure.transport.core.event_factory import PublishedEventFactory
from pyddd.infrastructure.transport.core.value_objects import PublishedEvent


class FakeNotification(INotification):
    def __init__(
            self,
            message_id: str,
            name: str,
            payload: dict,
    ):
        self._message_id = message_id
        self._name = name
        self._payload = payload

    @property
    def message_id(self) -> str:
        return self._message_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def payload(self) -> dict:
        return self._payload

    def ack(self):
        pass

    def reject(self, requeue: bool):
        pass


class TestPublishedEventDomainEventTranslator:
    def test_must_impl_interface(self):
        factory = PublishedEventFactory()
        assert isinstance(factory, IEventFactory)

    def test_translate_from_published_event(self):
        published_event = PublishedEvent(
            full_event_name='test.domain.FakeNotificationName',
            message_id=str(uuid.uuid4()),
            payload=json.dumps(dict(result=True)),
            timestamp=str(datetime.datetime(2020, 1, 1, 1, 1, 25).timestamp())
        )
        notification = FakeNotification(
            message_id=str(uuid.uuid4()),
            name='test:domain:FakeNotificationName',
            payload=published_event.__dict__,
        )
        factory = PublishedEventFactory()
        domain_event = factory.build_event(notification)
        assert domain_event.__domain__ == 'test.domain'
        assert domain_event.__topic__ == 'test.domain.FakeNotificationName'
        assert domain_event.__message_name__ == 'FakeNotificationName'
        assert domain_event.__timestamp__ == datetime.datetime(2020, 1, 1, 1, 1, 25)
        assert domain_event.to_dict() == dict(result=True)
