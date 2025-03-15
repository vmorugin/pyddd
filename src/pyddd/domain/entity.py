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
    def __reference__(self) -> IdType:
        ...


class IRootEntity(IEntity[IdType], abc.ABC):

    @abc.abstractmethod
    def register_event(self, event: DomainEvent):
        ...

    @abc.abstractmethod
    def collect_events(self) -> list[DomainEvent]:
        ...


class _EntityMeta(abc.ABCMeta):
    def __call__(cls, *args, __reference__: IdType = None, **kwargs):
        instance = super().__call__(*args, **kwargs)
        if not hasattr(instance, '_reference'):
            instance._reference = __reference__ or EntityUid(str(uuid.uuid4()))
        return instance


class Entity(IEntity[IdType], metaclass=_EntityMeta):
    _reference: IdType

    @property
    def __reference__(self) -> IdType:
        return self._reference

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.__reference__ == other.__reference__


class _RootEntityMeta(abc.ABCMeta):

    def __call__(cls, *args, __reference__: IdType = None, **kwargs):
        instance = super().__call__(*args, **kwargs)
        if not hasattr(instance, '_reference'):
            instance._reference = __reference__ or EntityUid(str(uuid.uuid4()))
        instance._events = []
        return instance


class RootEntity(IRootEntity[IdType], metaclass=_RootEntityMeta):
    _events: list[DomainEvent]
    _reference: IdType

    def register_event(self, event: DomainEvent):
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events

    @property
    def __reference__(self) -> IdType:
        return self._reference

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.__reference__ == other.__reference__
