import json
import typing as t
import uuid
from functools import (
    singledispatchmethod,
)
from importlib.metadata import version as meta_version

from pyddd.domain import IESRootEntity
from pyddd.domain.abstractions import (
    EntityUid,
    IdType,
    IEntity,
    IRootEntity,
    Version,
    IEvent,
    IMessageMeta,
    SnapshotProtocol,
)

pydantic_version = meta_version("pydantic")
if pydantic_version.startswith("2"):
    from pydantic import (
        BaseModel,
        PrivateAttr,
    )
    from pydantic._internal._model_construction import ModelMetaclass
elif pydantic_version.startswith("1"):
    from pydantic.main import ModelMetaclass, BaseModel, PrivateAttr  # type: ignore[no-redef]
else:
    raise ImportError("Can not import pydantic. Please setup pydantic >= 1.x.x <= 2.x.x")


class _EntityMeta(ModelMetaclass):
    def __call__(cls, *args, __reference__: IdType = None, __version__: int = 1, **kwargs):
        instance = super().__call__(*args, **kwargs)
        if not hasattr(instance, "_reference"):
            instance._reference = __reference__ or EntityUid(str(uuid.uuid4()))
        instance._version = Version(__version__)
        return instance


class Entity(IEntity[IdType], BaseModel, metaclass=_EntityMeta):
    _reference: IdType = PrivateAttr()
    _version: Version = PrivateAttr()

    @property
    def __reference__(self) -> IdType:
        return self._reference

    @property
    def __version__(self) -> Version:
        return self._version

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__reference__ == other.__reference__

    def __hash__(self):
        return hash(self._reference)


def increment_version(entity: IEntity):
    assert isinstance(entity, Entity)
    entity._version = Version(entity.__version__ + 1)


class _RootEntityMeta(_EntityMeta):
    def __call__(cls, *args, __reference__: IdType = None, __version__: int = 1, **kwargs):
        instance = super().__call__(*args, __reference__=__reference__, __version__=__version__, **kwargs)
        instance._events = []
        return instance


class RootEntity(IRootEntity[IdType], Entity, metaclass=_RootEntityMeta):
    _events: list[IEvent] = PrivateAttr()
    _reference: IdType = PrivateAttr()

    @property
    def __reference__(self) -> IdType:
        return self._reference

    def register_event(self, event: IEvent):
        self._events.append(event)

    def collect_events(self) -> t.Iterable[IEvent]:
        events = list(self._events)
        self._events.clear()
        return events


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


class _EventSourcedEntityMeta(_EntityMeta):
    def __call__(cls, *args, __reference__: IdType = None, __version__: int = 0, **kwargs):
        instance = super().__call__(*args, __reference__=__reference__, __version__=__version__, **kwargs)
        instance._events = []
        return instance


class ESRootEntity(IESRootEntity[IdType], Entity, metaclass=_EventSourcedEntityMeta):
    _events: list[IEvent]

    def trigger_event(self, event_type: IMessageMeta, **params):
        event = event_type(__version__=Version(self.__version__ + 1), **params)
        self.apply(event)
        self._events.append(event)

    def apply(self, event: IEvent):
        """
        Mutate the entity state based on the event.
        """
        next_version = Version(self.__version__ + 1)
        assert event.__version__ == next_version

        self.when(event)
        increment_version(self)

    @singledispatchmethod
    def when(self, event: IEvent) -> "ESRootEntity":
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

    def collect_events(self) -> t.Iterable[IEvent]:
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


when = getattr(ESRootEntity.when, "register")
