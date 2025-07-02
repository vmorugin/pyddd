import uuid

import pytest

from pyddd.domain import DomainEvent
from pyddd.domain.message import _DomainMessagesCollection, get_message_class


class ExampleEvent(DomainEvent, domain="test.collection"): ...


class TestDomainEventsCollection:
    def test_register_and_get(self):
        collection = _DomainMessagesCollection()
        collection.register(message_cls=ExampleEvent)
        assert collection.get_class(topic=str(ExampleEvent.__topic__)) == ExampleEvent

    def test_could_raise_exception_if_registered_twice(self):
        collection = _DomainMessagesCollection()
        collection.register(ExampleEvent)
        with pytest.raises(ValueError, match="Message test.collection.ExampleEvent already registered."):
            collection.register(ExampleEvent)

    def test_raise_exception_if_not_found(self):
        collection = _DomainMessagesCollection()
        topic = str(uuid.uuid4())
        with pytest.raises(ValueError, match=f"Could not find message {topic}"):
            collection.get_class(topic)


def test_could_get_event_by_topic():
    event = get_message_class(topic=str(ExampleEvent.__topic__))
    assert event is ExampleEvent
