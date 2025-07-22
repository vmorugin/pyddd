import pytest

from pyddd.domain.abstractions import (
    MessageType,
    Version,
)
from pyddd.domain.event_sourcing import DomainEvent as ESDomainEvent
from pyddd.domain.event import DomainEvent


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
        class VersionedEvent(DomainEvent, domain="test.event", version=2):
            @staticmethod
            def upcast_v1_v2(state): ...

        event = VersionedEvent(some_attr="123")
        assert VersionedEvent.__version__ == event.__version__ == Version(2)

    def test_could_raise_error_if_could_not_upcast(self):
        class BrokenVersionedEvent(DomainEvent, domain="test.event", version=2): ...

        with pytest.raises(ValueError):
            BrokenVersionedEvent.load(payload={}, version=1)

    def test_can_upcast(self):
        class VersionedEventV2(DomainEvent, domain="test.event"):
            some_attr: int

            @staticmethod
            def upcast_v1_v2(state):
                state["some_attr"] = 0

        event = VersionedEventV2()

        assert event.some_attr == 0

    def test_can_upcast_from_class_version(self):
        class VersionedEventV2(DomainEvent, domain="test.event", version=3):
            renamed_attr: int

            @staticmethod
            def upcast_v1_v2(state):
                assert False, "Should not be called"

            @staticmethod
            def upcast_v2_v3(state):
                state["renamed_attr"] = state["some_attr"]

        event = VersionedEventV2(some_attr=123, class_version=2)

        assert event.renamed_attr == 123


class ExampleESEvent(ESDomainEvent, domain="test.event"):
    some_attr: str


class TestESDomainEvent:
    def test_es_event(self):
        event = ExampleESEvent(
            some_attr="123",
            entity_reference="entity-1",
            entity_version=5,
        )

        assert event.__type__ == MessageType.EVENT
        assert event.to_dict() == {"some_attr": "123"}
        assert event.__domain__ == "test.event"
        assert event.__message_name__ == "ExampleESEvent"
        assert event.__topic__ == "test.event.ExampleESEvent"
        assert event.__version__ == 1
        assert event.__entity_reference__ == "entity-1"
        assert event.__entity_version__ == 5

    def test_could_raise_error_if_entity_reference_not_set(self):
        with pytest.raises(ValueError):
            ExampleESEvent(some_attr="123", entity_version=5)

    def test_could_raise_error_if_entity_version_not_set(self):
        with pytest.raises(ValueError):
            ExampleESEvent(some_attr="123", entity_reference="entity-1")

    def test_could_load(self):
        event = ExampleESEvent.load(payload=dict(some_attr="123"), entity_version=123, entity_reference="entity-1")
        assert event.some_attr == "123"
        assert event.__entity_reference__ == "entity-1"
        assert event.__entity_version__ == 123
