import datetime as dt

from pyddd.domain import (
    DomainEvent,
    DomainName,
)
from pyddd.infrastructure.persistence.event_store import (
    Converter,
    StoredEvent,
)


class FakeDomainEvent(DomainEvent, domain=DomainName("test.domain")):
    name: str


def test_stored_event_attributes():
    event = StoredEvent(
        body="{}",
        event_id=123,
        occurred_on=dt.datetime(2020, 1, 1, 1, 1, 1),
        full_name="test.domain.TestEventStored",
    )
    assert event.body == "{}"
    assert event.event_id == 123
    assert event.occurred_on == dt.datetime(2020, 1, 1, 1, 1, 1)
    assert event.full_name == "test.domain.TestEventStored"


def test_domain_event_to_stored_event():
    domain_event = FakeDomainEvent(name="str")
    stored_event = Converter.domain_event_to_stored_event(domain_event=domain_event, stored_event_id=1)
    assert stored_event.full_name == "test.domain.FakeDomainEvent"
    assert stored_event.body == '{"name":"str"}'
    assert stored_event.occurred_on == domain_event.__timestamp__
    assert stored_event.event_id == 1


def test_stored_event_to_domain_event():
    stored_event = StoredEvent(
        body='{"name": "str"}',
        event_id=1,
        occurred_on=dt.datetime(2020, 1, 1, 1, 1, 1),
        full_name="test.domain.TestEventStored",
    )
    domain_event = Converter.stored_event_to_domain_event(stored_event=stored_event)
    assert domain_event.__timestamp__ == stored_event.occurred_on
    assert domain_event.to_json() == stored_event.body
    assert domain_event.__topic__ == stored_event.full_name
