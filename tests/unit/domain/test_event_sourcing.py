import json
import uuid

from pyddd.domain import (
    SourcedDomainEvent,
    DomainName,
)
from pyddd.domain.abstractions import (
    Version,
    SnapshotProtocol,
)
from pyddd.domain.event_sourcing import (
    ESRootEntity,
    Snapshot,
)

__domain__ = DomainName("test.event-sourcing")


class SomeRootEntity(ESRootEntity[str]):
    name: str

    @classmethod
    def create(cls, name: str) -> "SomeRootEntity":
        return cls._create(EntityCreated, reference=str(uuid.uuid4()), name=name)

    def rename(self, name: str):
        self.trigger_event(EntityRenamed, name=name)

    def snapshot(self) -> SnapshotProtocol:
        return Snapshot(
            reference=self.__reference__,
            version=int(self.__version__),
            state=self.json().encode(),
        )

    @classmethod
    def from_snapshot(cls, snapshot: SnapshotProtocol):
        state = json.loads(snapshot.__state__)
        return cls(
            __reference__=snapshot.__entity_reference__,
            __version__=Version(snapshot.__entity_version__),
            name=state["name"],
        )


class EntityCreated(SourcedDomainEvent, domain=__domain__):
    name: str

    def mutate(self, entity: None) -> SomeRootEntity:
        obj = SomeRootEntity(
            __reference__=self.__entity_reference__,
            __version__=self.__entity_version__,
            name=self.name,
        )
        return obj


class EntityRenamed(SourcedDomainEvent, domain=__domain__):
    name: str

    def apply(self, aggregate: SomeRootEntity) -> None:
        aggregate.name = self.name


class TestEventSourcedEntity:
    def test_has_version(self):
        entity = SomeRootEntity(name="before", __version__=10)
        assert entity.__version__ == Version(10)

    def test_could_be_restored_from_events(self):
        entity = SomeRootEntity.create(name="before")
        entity.rename("after")
        events = list(entity.collect_events())
        assert len(events) == 2

        new = None
        for event in events:
            new = event.mutate(new)

        assert isinstance(new, SomeRootEntity)
        assert new == entity
        assert new.name == entity.name == "after"
        assert new.__version__ == Version(2)

    def test_could_make_snapshot_and_load(self):
        entity = SomeRootEntity(name="123")
        snapshot = entity.snapshot()
        assert SomeRootEntity.from_snapshot(snapshot) == entity

    def test_could_update_version_when_apply_event(self):
        entity = SomeRootEntity(name="123")
        entity.trigger_event(EntityRenamed, name="456")
        assert entity.__version__ == Version(2)

    def test_must_update_entity_and_event_version_when_trigger(self):
        entity = SomeRootEntity(name="123", __version__=1)
        entity.trigger_event(EntityRenamed, name="456")
        entity.trigger_event(EntityRenamed, name="567")
        events = list(entity.collect_events())
        last_version = Version(3)
        while events:
            event = events.pop()
            assert event.__entity_version__ == last_version
            last_version = Version(last_version - 1)
