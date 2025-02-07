import abc
import typing as t

from domain.event import DomainEvent


class ValueObject:
    ...


T = t.TypeVar('T')


class IEntity(t.Generic[T], abc.ABC):
    @property
    @abc.abstractmethod
    def reference(self) -> T:
        ...


class IRootEntity(IEntity[T], abc.ABC):

    @abc.abstractmethod
    def register_event(self, event: DomainEvent):
        ...

    @abc.abstractmethod
    def collect_events(self) -> list[DomainEvent]:
        ...


class Entity(IEntity[T]):
    def __init__(self, reference: T):
        self._reference = reference

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.reference == other.reference

    @property
    def reference(self) -> T:
        return self._reference


class RootEntity(IRootEntity[T]):
    def __init__(self, reference: T):
        self._reference = reference
        self._events = []

    def register_event(self, event: DomainEvent):
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = self._events
        self._events = []
        return events

    @property
    def reference(self) -> T:
        return self._reference
