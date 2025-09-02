import typing as t
import uuid

import pytest

from pyddd.domain import (
    DomainName,
)
from pyddd.domain.abstractions import (
    Version,
    IdType,
    IESEvent,
)
from pyddd.domain.event_sourcing import (
    Entity,
    RootEntity,
    DomainEvent,
)

__domain__ = DomainName("test.event-sourcing")


class BaseEvent(DomainEvent, domain=__domain__): ...


class EntityCreated(BaseEvent):
    name: str

    def mutate(self, _: None) -> "SomeRootEntity":
        entity = SomeRootEntity(__reference__=self.__entity_reference__, __version__=self.__entity_version__)
        entity._state = SomeState(__reference__=self.__entity_reference__, name=self.name)
        return entity


class EntityRenamed(BaseEvent):
    name: str

    def apply(self, entity: "SomeRootEntity"):
        entity._state.name = self.name


class SomeState(Entity):
    name: str


class SomeRootEntity(RootEntity[str]):
    _state: SomeState

    @classmethod
    def create(cls, name: str) -> "RootEntity":
        reference = str(uuid.uuid4())
        return cls._create(EntityCreated, reference=reference, name=name)

    @classmethod
    def restore(cls, reference: IdType, events: t.Iterable[IESEvent]) -> "SomeRootEntity":
        self = cls(__reference__=reference, __version__=1)
        for event in events:
            self = event.mutate(self)
        return self

    def rename(self, name: str):
        self.trigger_event(EntityRenamed, name=name, old_name=self._state.name)

    @property
    def name(self):
        return self._state.name

    def created(self, event: EntityCreated):
        state = SomeState(__reference__=event.__entity_reference__, name=event.name)
        self._state = state


class TestEventSourcedEntity:
    def test_has_version(self):
        entity = SomeRootEntity(__version__=10)
        assert entity.__version__ == Version(10)

    def test_could_be_restored_from_events(self):
        entity = SomeRootEntity.create(name="before")
        entity.rename("after")
        events = list(entity.collect_events())
        assert len(events) == 2

        new = SomeRootEntity.restore(reference=entity.__reference__, events=events)

        assert isinstance(new, SomeRootEntity)
        assert new == entity
        assert new.name == entity.name == "after"
        assert new.__version__ == entity.__version__
        assert new.__reference__ == entity.__reference__

    def test_could_mutate_when_apply(self):
        entity = SomeRootEntity.create(name="123")
        entity.trigger_event(EntityRenamed, name="456", old_name="123")
        assert entity.name == "456"

    def test_must_update_entity_and_event_version_when_trigger(self):
        entity = SomeRootEntity.create(name="123")
        entity.trigger_event(EntityRenamed, name="456")
        entity.trigger_event(EntityRenamed, name="567")
        events = list(entity.collect_events())
        last_version = Version(3)
        while events:
            event = events.pop()
            assert event.__entity_version__ == last_version
            last_version = Version(last_version - 1)

    def test_could_update_version_when_mutate(self):
        entity = SomeRootEntity.create(name="123")
        event = EntityRenamed(name="456", entity_version=2, entity_reference=str(entity.__reference__))
        event.mutate(entity)
        assert entity.__version__ == Version(2)

    def test_could_not_apply_event_with_wrong_reference(self):
        entity = SomeRootEntity.create(name="123")
        event = EntityRenamed(name="456", entity_version=2, entity_reference="wrong_reference")
        with pytest.raises(AssertionError):
            event.mutate(entity)
