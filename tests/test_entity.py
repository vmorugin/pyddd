import uuid

from pyddd.domain.entity import (
    Entity,
    RootEntity,
    EntityUid,
)
from pyddd.domain import DomainEvent


class TestEntity:
    def test_entity(self):
        class SomeEntity(Entity[str]):
            ...

        entity = SomeEntity(reference='123')
        assert entity.reference == '123'
        assert entity == SomeEntity(reference='123')

    def test_entity_eq(self):
        class SomeEntity(Entity[str]):
            ...

        reference = str(uuid.uuid4())
        assert SomeEntity(reference=reference) == SomeEntity(reference=reference)

    def test_can_init_with_custom_attributes(self):
        class SomeEntity(Entity):
            def __init__(self, name: str):
                self.name = name

        entity = SomeEntity(name='Test')
        assert entity.name == 'Test'

    def test_can_init_with_default_reference(self):
        class SomeEntity(Entity):
            ...

        entity = SomeEntity()
        assert isinstance(entity.reference, EntityUid)


class TestRootEntity:
    def test_root(self):
        class SomeRootEntity(RootEntity[int]):
            ...

        class TestEvent(DomainEvent, domain='test'):
            ...

        entity = SomeRootEntity(reference=123)
        event = TestEvent()
        entity.register_event(event)
        assert entity.collect_events() == [event]
        assert entity.collect_events() == []

    def test_entity_eq(self):
        class SomeEntity(RootEntity[str]):
            ...

        reference = str(uuid.uuid4())
        assert SomeEntity(reference=reference) == SomeEntity(reference=reference)

    def test_can_init_with_default_reference(self):
        class SomeEntity(RootEntity):
            ...

        entity = SomeEntity()
        assert isinstance(entity.reference, EntityUid)