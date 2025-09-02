import uuid

import pytest

from pyddd.domain import DomainEvent
from pyddd.domain.abstractions import MessageTopic
from pyddd.domain.message import (
    _DomainMessagesCollection,
    get_message_class,
    register_message_alias,
)


class ExampleEvent(DomainEvent, domain="test.collection"): ...


class AnotherExampleEvent(DomainEvent, domain="test.collection"): ...


class TestDomainEventsCollection:
    def test_register_and_get(self):
        collection = _DomainMessagesCollection()
        collection.register(topic=MessageTopic(ExampleEvent.__topic__), message_cls=ExampleEvent)
        assert collection.get_class(topic=MessageTopic(ExampleEvent.__topic__)) == ExampleEvent

    def test_idempotent_with_the_same_cls(self):
        collection = _DomainMessagesCollection()
        collection.register(MessageTopic(ExampleEvent.__topic__), ExampleEvent)
        collection.register(MessageTopic(ExampleEvent.__topic__), ExampleEvent)

    def test_must_raise_error_if_already_registered_topic_another_cls(self):
        collection = _DomainMessagesCollection()
        collection.register(str(ExampleEvent.__topic__), ExampleEvent)
        with pytest.raises(
            ValueError, match="Message test.collection.ExampleEvent already registered by another class."
        ):
            collection.register(MessageTopic(ExampleEvent.__topic__), AnotherExampleEvent)

    def test_raise_exception_if_get_not_registered(self):
        collection = _DomainMessagesCollection()
        topic = str(uuid.uuid4())
        with pytest.raises(ValueError, match=f"Could not find message {topic}"):
            collection.get_class(topic)


def test_could_get_event_by_topic():
    event = get_message_class(topic=MessageTopic(ExampleEvent.__topic__))
    assert event is ExampleEvent


def test_could_register_alias():
    register_message_alias(alias="some.alias.ExampleOldEvent", message_cls=ExampleEvent)
    event = get_message_class(topic=MessageTopic(ExampleEvent.__topic__))
    assert event is ExampleEvent
