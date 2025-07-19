import typing as t
import uuid
from importlib.metadata import version as meta_version

from pyddd.domain.abstractions import (
    EntityUid,
    IdType,
    IEntity,
    IRootEntity,
    Version,
    IEvent,
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
