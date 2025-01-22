from domain.entity import (
    Entity,
    RootEntity,
)
from domain import DomainEvent


class TestEntity:
    def test_entity(self):
        class SomeEntity(Entity[str]):
            ...

        entity = SomeEntity(__reference__='123')
        assert entity.__reference__ == '123'
        assert entity == SomeEntity(__reference__='123')

class TestRootEntity:
    def test_root(self):
        class SomeRootEntity(RootEntity[int]):
            ...

        class TestEvent(DomainEvent, domain='test'):
            ...

        entity = SomeRootEntity(__reference__=123)
        event = TestEvent()
        entity.register_event(event)
        assert entity.collect_events() == [event]
        assert entity.collect_events() == []