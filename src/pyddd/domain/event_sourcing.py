import json
import typing as t
import datetime as dt
from uuid import UUID

from pydantic import PrivateAttr

from pyddd.domain.abstractions import (
    ISourcedEvent,
    IdType,
    Version,
    ISourcedEventMeta,
    IESRootEntity,
    SnapshotProtocol,
)
from pyddd.domain.entity import (
    Entity,
    _EntityMeta,
    increment_version,
)
from pyddd.domain.message import (
    BaseDomainMessage,
    BaseDomainMessageMeta,
)

ESEntityT = t.TypeVar("ESEntityT", bound=IESRootEntity)


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


class SourcedDomainEventMeta(BaseDomainMessageMeta, ISourcedEventMeta):
    def __init__(cls, name, bases, namespace, *, domain: t.Optional[str] = None):
        super().__init__(name, bases, namespace, domain=domain)
        if domain is None and cls.__module__ != __name__:
            try:
                _ = cls.__domain__
            except AttributeError:
                raise ValueError(f"required set domain name for '{cls.__module__}.{cls.__name__}'")

    def __call__(cls, *args, entity_reference: IdType = None, entity_version: Version = None, **kwargs):
        instance = super().__call__(*args, **kwargs)
        if entity_reference is None or entity_version is None:
            raise AttributeError(
                f"Required to set entity_reference and entity_version attributes for '{cls.__module__}.{cls.__name__}'"
            )
        instance._entity_reference = entity_reference
        instance._entity_version = entity_version
        return instance

    def load(
        cls,
        payload: t.Mapping | str | bytes,
        message_id: UUID | None = None,
        timestamp: dt.datetime | None = None,
        **kwargs,
    ):
        obj: SourcedDomainEvent = super().load(payload, message_id, timestamp, **kwargs)  # type: ignore[misc]
        entity_reference, entity_version = kwargs.get("entity_reference"), kwargs.get("entity_version")
        if entity_reference is None or entity_version is None:
            raise AttributeError(
                f"Required to set entity_reference and entity_version attributes for '{cls.__module__}.{cls.__name__}'"
            )
        obj._entity_reference = str(kwargs["entity_reference"])
        obj._entity_version = Version(kwargs["entity_version"])
        return obj


class SourcedDomainEvent(BaseDomainMessage, ISourcedEvent, metaclass=SourcedDomainEventMeta):
    _entity_reference: str = PrivateAttr()
    _entity_version: Version = PrivateAttr()

    @property
    def __entity_reference__(self) -> str:
        return self._entity_reference

    @property
    def __entity_version__(self) -> Version:
        return self._entity_version

    def mutate(self, entity: t.Optional[ESEntityT]) -> ESEntityT:
        assert entity is not None

        next_version = entity.__version__ + 1
        assert self.__entity_version__ == next_version

        self.apply(entity)

        increment_version(entity)

        return entity

    def apply(self, entity: ESEntityT) -> None: ...


class _EventSourcedEntityMeta(_EntityMeta):
    def __call__(cls, *args, __reference__: IdType = None, __version__: int = 1, **kwargs):
        instance = super().__call__(*args, __reference__=__reference__, __version__=__version__, **kwargs)
        instance._events = []
        instance._init_version = Version(__version__)
        return instance


class ESRootEntity(IESRootEntity[IdType, SourcedDomainEvent], Entity, metaclass=_EventSourcedEntityMeta):
    _events: list[SourcedDomainEvent] = PrivateAttr()
    _reference: IdType = PrivateAttr()

    @classmethod
    def _create(cls, event_type: ISourcedEventMeta, reference: IdType, **params):
        created = event_type(entity_reference=reference, entity_version=Version(1), **params)
        obj = created.mutate(None)
        obj.register_event(created)
        return obj

    def trigger_event(self, event_type: ISourcedEventMeta, **params):
        event = event_type(
            entity_reference=self.__reference__,
            entity_version=Version(self.__version__ + 1),
            **params,
        )
        event.apply(self)
        increment_version(self)
        self._events.append(event)

    def register_event(self, event: SourcedDomainEvent):
        self._events.append(event)

    def collect_events(self) -> t.Iterable[SourcedDomainEvent]:
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
