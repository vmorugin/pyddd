import typing as t
import uuid
from importlib.metadata import version
from pyddd.domain.abstractions import (
    EntityUid,
    IdType,
    IEvent,
    IEntity,
    IRootEntity,
)

pydantic_version = version("pydantic")
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
    def __call__(cls, *args, __reference__: IdType = None, **kwargs):
        instance = super().__call__(*args, **kwargs)
        if not hasattr(instance, "_reference"):
            instance._reference = __reference__ or EntityUid(str(uuid.uuid4()))
        return instance


class Entity(IEntity[IdType], BaseModel, t.Generic[IdType], metaclass=_EntityMeta):
    _reference: IdType = PrivateAttr()

    @property
    def __reference__(self) -> IdType:
        return self._reference

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__reference__ == other.__reference__

    def __hash__(self):
        return hash(self._reference)


class _RootEntityMeta(_EntityMeta):
    def __call__(cls, *args, __reference__: IdType = None, **kwargs):
        instance = super().__call__(*args, __reference__=__reference__, **kwargs)
        instance._events = []
        return instance


class RootEntity(IRootEntity[IdType], Entity, t.Generic[IdType], metaclass=_RootEntityMeta):
    _events: list[IEvent] = PrivateAttr()
    _reference: IdType = PrivateAttr()

    def register_event(self, event: IEvent):
        self._events.append(event)

    def collect_events(self) -> list[IEvent]:
        events = list(self._events)
        self._events.clear()
        return events

    @property
    def __reference__(self) -> IdType:
        return self._reference
