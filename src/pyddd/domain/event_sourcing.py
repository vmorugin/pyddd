import datetime as dt
import json
import typing as t
from functools import singledispatchmethod
from typing import Mapping
from uuid import UUID

from pyddd.domain.entity import (
    _EntityMeta,
    Entity,
    increment_version,
)
from pyddd.domain.message import (
    BaseDomainMessageMeta,
    _T,
    BaseDomainMessage,
)
from pyddd.domain.abstractions import (
    IESEvent,
    IdType,
    IESEventMeta,
    IESRootEntity,
    Version,
    SnapshotProtocol,
)


class _ESDomainEventMeta(BaseDomainMessageMeta, IESEventMeta):
    def __init__(cls, name, bases, namespace, *, domain: t.Optional[str] = None, version: int = 1):
        super().__init__(name, bases, namespace, domain=domain, version=version)
        if domain is None and cls.__module__ != __name__:
            try:
                _ = cls.__domain__
            except AttributeError:
                raise ValueError(f"required set domain name for '{cls.__module__}.{cls.__name__}'")

    def __call__(cls, *args, entity_reference: IdType = None, entity_version: int = None, **kwargs):
        instance = super().__call__(*args, **kwargs)
        cls._set_entity_reference_and_version(
            instance=instance, entity_reference=entity_reference, entity_version=entity_version
        )
        return instance

    def load(  # type: ignore[misc]
        cls: type[_T],
        payload: Mapping | str | bytes,
        message_id: UUID | None = None,
        timestamp: dt.datetime | None = None,
        **kwargs,
    ) -> _T:
        obj = super().load(payload, message_id, timestamp, **kwargs)  # type: ignore[misc]
        _ESDomainEventMeta._set_entity_reference_and_version(
            instance=obj,
            entity_reference=kwargs.get("entity_reference"),
            entity_version=kwargs.get("entity_version"),
        )
        return obj

    @classmethod
    def _set_entity_reference_and_version(
        cls, instance, entity_reference: IdType = None, entity_version: int = None
    ) -> None:
        if entity_reference is None or entity_version is None:
            raise ValueError(
                f"required to set entity_reference and entity_version for '{cls.__module__}.{cls.__name__}'"
            )
        instance._entity_reference = entity_reference
        instance._entity_version = entity_version


class DomainEvent(BaseDomainMessage, IESEvent, metaclass=_ESDomainEventMeta):
    _entity_reference: str
    _entity_version: int

    @property
    def __entity_reference__(self) -> str:
        return self._entity_reference

    @property
    def __entity_version__(self) -> int:
        return self._entity_version


class _EventSourcedEntityMeta(_EntityMeta):
    def __call__(cls, *args, __reference__: IdType = None, __version__: int = 0, **kwargs):
        instance = super().__call__(*args, __reference__=__reference__, __version__=__version__, **kwargs)
        instance._events = []
        return instance


class Snapshot:
    def __init__(self, state: bytes, reference: str, version: int):
        self._state = state
        self._reference = reference
        self._version = version

    @property
    def __state__(self) -> bytes:
        return self._state

    @property
    def __entity_reference__(self) -> str:
        return self._reference

    @property
    def __entity_version__(self) -> int:
        return self._version


class RootEntity(IESRootEntity[IdType], Entity, metaclass=_EventSourcedEntityMeta):
    _events: list[IESEvent]

    def trigger_event(self, event_type: IESEventMeta, **params):
        event = event_type(entity_version=self.__version__ + 1, entity_reference=str(self.__reference__), **params)
        self.apply(event)
        self._events.append(event)

    def apply(self, event: IESEvent):
        """
        Mutate the entity state based on the event.
        """
        next_version = Version(self.__version__ + 1)
        assert event.__entity_version__ == next_version

        self.when(event)
        increment_version(self)

    @singledispatchmethod
    def when(self, event: IESEvent) -> "RootEntity":
        """
        Implement the method to apply events by type.

        Example:
        from pyddd.entity import when

        ...

        @when
        def _(self, event: EntityCreated):
            state = State(name=event.name)
            self._state = state

        @when
        def _(self, event: EntityRenamed):
            self._state.name = event.name
        """

        raise NotImplementedError(f"Mutate method not implemented for event type: {type(event)}")

    def collect_events(self) -> t.Iterable[IESEvent]:
        events = self._events
        self._events = []
        yield from events

    def snapshot(self) -> SnapshotProtocol:
        return Snapshot(
            reference=self.__reference__,
            version=int(self.__version__),
            state=self.json().encode(),
        )

    @classmethod
    def from_snapshot(cls, snapshot: SnapshotProtocol):
        state = json.loads(snapshot.__state__)
        return cls(
            __reference__=snapshot.__entity_reference__,
            __version__=Version(snapshot.__entity_version__),
            **state,
        )


when = getattr(RootEntity.when, "register")
