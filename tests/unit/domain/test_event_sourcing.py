import dataclasses
import json
import uuid

from pyddd.domain import (
    SourcedDomainEvent,
    DomainName,
)
from pyddd.domain.abstractions import (
    Version,
    SnapshotABC,
)
from pyddd.domain.entity import increment_version
from pyddd.domain.event_sourcing import EventSourcedEntity

__domain__ = DomainName("test.event-sourcing")


@dataclasses.dataclass(frozen=True)
class SomeRootEntitySnapshot(SnapshotABC):
    reference: str
    version: int
    name: str

    @property
    def __state__(self) -> bytes:
        return json.dumps(self.__dict__).encode()

    @property
    def __entity_reference__(self):
        return self.reference

    @property
    def __entity_version__(self) -> int:
        return self.version


class SomeRootEntity(EventSourcedEntity[str]):
    name: str

    @classmethod
    def create(cls, name: str) -> "SomeRootEntity":
        return cls._create(EntityCreated, reference=str(uuid.uuid4()), name=name)

    def rename(self, name: str):
        self.trigger_event(EntityRenamed, name=name)

    def snapshot(self) -> SomeRootEntitySnapshot:
        return SomeRootEntitySnapshot(
            reference=self.__reference__,
            version=int(self.__version__),
            name=self.name,
        )

    @classmethod
    def from_snapshot(cls, snapshot: SomeRootEntitySnapshot):
        return cls(
            __reference__=snapshot.reference,
            __version__=Version(snapshot.version),
            name=snapshot.name,
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
    def test_entity_has_init_version(self):
        entity = SomeRootEntity(name="before")
        increment_version(entity)
        assert entity.__init_version__ == Version(1)

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

        assert entity.__version__ == Version(2)

    def test_could_make_snapshot_and_load(self):
        entity = SomeRootEntity(name="123")
        snapshot = entity.snapshot()
        assert SomeRootEntity.from_snapshot(snapshot) == entity

    def test_could_update_version_when_apply_event(self):
        entity = SomeRootEntity(name="123")
        entity.trigger_event(EntityRenamed, name="456")
        assert entity.__version__ == 2
        events = list(entity.collect_events())
        event = events.pop()
        assert event.__entity_version__ == 2
