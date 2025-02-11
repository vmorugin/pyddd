import abc
import typing as t
import uuid
from uuid import UUID

from pyddd.domain.event import DomainEvent


class ValueObject:
    ...


class EntityUid(ValueObject, UUID):
    ...

IdType = t.TypeVar('IdType')


class IEntity(t.Generic[IdType], abc.ABC):
    @property
    @abc.abstractmethod
    def reference(self) -> IdType:
        ...


class IRootEntity(IEntity[IdType], abc.ABC):

    @abc.abstractmethod
    def register_event(self, event: DomainEvent):
        ...

    @abc.abstractmethod
    def collect_events(self) -> list[DomainEvent]:
        ...


class _EntityMeta(abc.ABCMeta):
    def __call__(cls, *args, reference: IdType = None, **kwargs):
        if reference is None:
            reference = EntityUid(str(uuid.uuid4()))
        cls._reference = reference
        return super().__call__(*args, **kwargs)


class Entity(IEntity[IdType], metaclass=_EntityMeta):

    @property
    def reference(self) -> IdType:
        return self._reference

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.reference == other.reference


class _RootEntityMeta(abc.ABCMeta):

    def __call__(cls, *args, reference: IdType = None, **kwargs):
        if reference is None:
            reference = EntityUid(str(uuid.uuid4()))
        cls._reference = reference
        cls._events = []
        return super().__call__(*args, **kwargs)


class RootEntity(IRootEntity[IdType], metaclass=_RootEntityMeta):

    def register_event(self, event: DomainEvent):
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events

    @property
    def reference(self) -> IdType:
        return self._reference

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.reference == other.reference
