from domain.entity import (
    Entity,
    RootEntity,
)
from domain import DomainEvent


class TestEntity:
    def test_entity(self):
        class SomeEntity(Entity[str]):
            ...

        entity = SomeEntity(reference='123')
        assert entity.reference == '123'
        assert entity == SomeEntity(reference='123')

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