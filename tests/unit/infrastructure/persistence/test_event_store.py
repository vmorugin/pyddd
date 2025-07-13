import uuid

import pytest

from pyddd.domain import (
    DomainEvent,
)
from pyddd.domain.abstractions import (
    Version,
)
from pyddd.domain.entity import (
    ESRootEntity,
    Snapshot,
)
from pyddd.infrastructure.persistence.abstractions import (
    IEventStore,
)
from pyddd.infrastructure.persistence.event_store import OptimisticConcurrencyError
from pyddd.infrastructure.persistence.event_store.in_memory import InMemoryStore


class EntityCreated(DomainEvent, domain="test.event-store"):
    name: str

    def mutate(self, entity: None):
        return ExampleEntity(
            __reference__=self.__entity_reference__,
            __version__=self.__entity_version__,
            name=self.name,
        )


class EntityRenamed(DomainEvent, domain="test.event-store"):
    name: str

    def apply(self, entity: "ExampleEntity") -> None:
        entity.name = self.name


class ExampleEntity(ESRootEntity[str]):
    name: str

    @classmethod
    def create(cls, name: str) -> "ExampleEntity":
        return cls._create(EntityCreated, reference=str(uuid.uuid4()), name=name)

    def rename(self, name: str):
        self.trigger_event(EntityRenamed, name=name)


class TestInMemoryEventStore:
    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.fixture
    def stream_name(self):
        return str(uuid.uuid4())

    def test_must_impl(self, store):
        assert isinstance(store, IEventStore)

    def test_could_get_empty_stream(self, store, stream_name):
        assert list(store.get_stream(stream_name, 0, 100)) == []

    def test_could_append_to_stream(self, store, stream_name):
        events = [EntityCreated(entity_reference=str(uuid.uuid4()), entity_version=Version(1), name="123")]
        store.append_to_stream(stream_name, events)
        assert store.get_stream(stream_name, 0, 1) == events

    def test_could_raise_error_if_conflict_of_version(self, store, stream_name):
        events = [EntityCreated(__version__=Version(1), name="123")]
        store.append_to_stream(stream_name, events)
        with pytest.raises(
            OptimisticConcurrencyError, match=f"Conflict version of stream {stream_name}. Version 1 exists"
        ):
            store.append_to_stream(stream_name, events)

    def test_could_add_and_get_snapshot(self, store, stream_name):
        store.add_snapshot(stream_name, Snapshot(state=b"{}", version=1, reference="123"))
        snapshot = store.get_last_snapshot(stream_name)
        assert snapshot.__state__ == b"{}"
        assert snapshot.__entity_version__ == 1
        assert snapshot.__entity_reference__ == "123"

    def test_could_get_none_if_not_created_snapshot(self, store, stream_name):
        assert store.get_last_snapshot(stream_name) is None
