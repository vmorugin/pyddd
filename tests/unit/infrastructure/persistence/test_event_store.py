import uuid

import pytest

from pyddd.domain import (
    SourcedDomainEvent,
)
from pyddd.domain.abstractions import (
    Version,
)
from pyddd.domain.event_sourcing import (
    Snapshot,
    SourcedEntityT,
    EventSourcedEntity,
)
from pyddd.infrastructure.persistence.abstractions import (
    IEventStore,
    IESRepository,
)
from pyddd.infrastructure.persistence.event_store import OptimisticConcurrencyError
from pyddd.infrastructure.persistence.event_store.in_memory import InMemoryStore
from pyddd.infrastructure.persistence.event_store.repository import (
    EventSourcedRepository,
)


class EntityCreated(SourcedDomainEvent, domain="test.event-store"):
    name: str

    def mutate(self, entity: None) -> SourcedEntityT:
        return ExampleEntity(
            __reference__=self.__entity_reference__,
            __version__=self.__entity_version__,
            name=self.name,
        )


class EntityRenamed(SourcedDomainEvent, domain="test.event-store"):
    name: str

    def apply(self, entity: "ExampleEntity") -> None:
        entity.name = self.name


class ExampleEntity(EventSourcedEntity[str]):
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
        assert list(store.get_from_stream(stream_name, 0, 100)) == []

    def test_could_append_to_stream(self, store, stream_name):
        events = [EntityCreated(entity_reference=str(uuid.uuid4()), entity_version=Version(1), name="123")]
        store.append_to_stream(stream_name, events)
        assert store.get_from_stream(stream_name, 0, 1) == events

    def test_could_raise_error_if_conflict_of_version(self, store, stream_name):
        events = [EntityCreated(entity_reference=str(uuid.uuid4()), entity_version=Version(1), name="123")]
        store.append_to_stream(stream_name, events)
        with pytest.raises(
            OptimisticConcurrencyError, match=f"Conflict version of stream {stream_name}. Expected version 2 found 1"
        ):
            store.append_to_stream(stream_name, events, expected_version=2)

    def test_could_add_and_get_snapshot(self, store, stream_name):
        store.add_snapshot(stream_name, Snapshot(state=b"{}", version=1, reference="123"))
        snapshot = store.get_last_snapshot(stream_name)
        assert snapshot.__state__ == b"{}"
        assert snapshot.__entity_version__ == 1
        assert snapshot.__entity_reference__ == "123"

    def test_could_get_none_if_not_created_snapshot(self, store, stream_name):
        assert store.get_last_snapshot(stream_name) is None


class TestEventSourcedRepository:
    @pytest.fixture
    def event_store(self):
        return InMemoryStore()

    @pytest.fixture
    def repository(self, event_store) -> IESRepository[ExampleEntity]:
        return EventSourcedRepository(
            event_store=event_store, snapshot_store=event_store, entity_cls=ExampleEntity, snapshot_interval=2
        )

    def test_must_impl(self, repository):
        assert isinstance(repository, IESRepository)

    def test_could_add_and_get(self, repository):
        entity = ExampleEntity.create("Test")
        repository.add(entity)
        repository.commit()
        new = repository.find_by(entity.__reference__)
        assert new == entity

    def test_could_get_from_snapshot(self, event_store, repository):
        entity = ExampleEntity.create("Test")
        event_store.add_snapshot(str(entity.__reference__), entity.snapshot())
        new = repository.find_by(entity.__reference__)
        assert new == entity
        assert new.name == "Test"

    def test_get_and_update(self, repository):
        entity = ExampleEntity.create("Test")
        repository.add(entity)
        repository.commit()

        new = repository.find_by(entity.__reference__)
        new.rename("New Name")
        repository.commit()

        updated = repository.find_by(entity.__reference__)

        assert updated.name == "New Name"
