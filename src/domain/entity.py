import abc
import typing as t
from dataclasses import (
    dataclass,
    field,
)

from domain.event import DomainEvent

T = t.TypeVar('T')


class ValueObject(t.Hashable, abc.ABC):

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__hash__() == other.__hash__()


class EntityId(ValueObject):
    @classmethod
    @abc.abstractmethod
    def generate(cls, *args, **kwargs) -> 'EntityId':
        ...

@dataclass(kw_only=True)
class Entity(t.Generic[T]):
    __reference__: T


@dataclass(kw_only=True)
class RootEntity(Entity[T]):
    _events: list[DomainEvent] = field(default_factory=list)

    def register_event(self, event: DomainEvent):
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events