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

        entity = SomeEntity(__reference__='123')
        assert entity.__reference__ == '123'
        assert entity == SomeEntity(__reference__='123')

    def test_entity_neq(self):
        class SomeEntity(Entity[str]):
            ...

        assert SomeEntity() != SomeEntity()

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
        assert isinstance(entity.__reference__, EntityUid)


class TestRootEntity:
    def test_root(self):
        class SomeRootEntity(RootEntity[int]):
            ...

        class ExampleEvent(DomainEvent, domain='test'):
            ...

        entity = SomeRootEntity(__reference__=123)
        assert entity == SomeRootEntity(__reference__=123)
        assert entity.__reference__ == 123

        event = ExampleEvent()
        entity.register_event(event)
        assert entity.collect_events() == [event]
        assert entity.collect_events() == []

    def test_entityn_eq(self):
        class SomeEntity(RootEntity[str]):
            ...

        assert SomeEntity() != SomeEntity()

    def test_can_init_with_default_reference(self):
        class SomeEntity(RootEntity):
            ...

        entity = SomeEntity()
        assert isinstance(entity.__reference__, EntityUid)