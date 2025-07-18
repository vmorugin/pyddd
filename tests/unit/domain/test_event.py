import pytest

from pyddd.domain import DomainEvent
from pyddd.domain.abstractions import (
    MessageType,
    Version,
)


class ExampleEvent(DomainEvent, domain="test.event"):
    some_attr: str


class TestDomainEvent:
    def test_event(self):
        event = ExampleEvent(some_attr="123")

        assert event.__type__ == MessageType.EVENT
        assert event.to_dict() == {"some_attr": "123"}
        assert event.__domain__ == "test.event"
        assert event.__message_name__ == "ExampleEvent"
        assert event.__topic__ == "test.event.ExampleEvent"
        assert event.__version__ == 1

    def test_attrs_from_cls(self):
        assert ExampleEvent.__message_name__ == "ExampleEvent"
        assert ExampleEvent.__domain__ == "test.event"
        assert ExampleEvent.__topic__ == "test.event.ExampleEvent"

    def test_event_without_domain(self):
        with pytest.raises(ValueError):

            class ExampleEvent(DomainEvent): ...

    def test_could_create_with_version(self):
        class VersionedEvent(DomainEvent, domain="test.event"): ...

        event = VersionedEvent(__version__=2)
        assert event.__version__ == Version(2)
