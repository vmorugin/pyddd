import sys
import typing as t
from pyddd.domain.abstractions import (
    IdType,
    ISourcedEvent,
)
from pyddd.domain.event_sourcing import SourcedEntityT
from pyddd.infrastructure.persistence.abstractions import (
    IESRepository,
    IEventStore,
    ISnapshotStore,
)


class EventSourcedRepository(IESRepository[SourcedEntityT]):
    def __init__(self, event_store: IEventStore):
        self._events = event_store
        self._seen: dict[str, SourcedEntityT] = {}

    def add(self, entity: SourcedEntityT):
        self._seen[str(entity.__reference__)] = entity

    def find_by(self, entity_id: IdType) -> t.Optional[SourcedEntityT]:
        entity: t.Optional[SourcedEntityT] = None
        stream = self._events.get_from_stream(str(entity_id), from_version=0, to_version=sys.maxsize)
        for event in stream:
            entity = t.cast(SourcedEntityT, event.mutate(entity))
        if entity:
            self._seen[str(entity.__reference__)] = entity
        return entity

    def commit(self):
        for reference, entity in self._seen.items():
            self._events.append_to_stream(reference, events=entity.collect_events())
        self._seen.clear()


class SnapshotEventSourcedRepository(IESRepository[SourcedEntityT]):
    def __init__(
        self,
        event_store: IEventStore,
        entity_cls: type[SourcedEntityT],
        snapshot_store: ISnapshotStore,
        snapshot_interval: int,
    ):
        self._entity_cls = entity_cls
        self._events = event_store
        self._snapshots = snapshot_store
        self._interval = snapshot_interval
        self._seen: dict[str, SourcedEntityT] = {}

    def find_by(self, entity_id: IdType) -> t.Optional[SourcedEntityT]:
        entity = self._rehydrate(str(entity_id), entity=None, from_version=0, to_version=sys.maxsize)
        if entity:
            self._seen[str(entity.__reference__)] = entity
        return entity

    def add(self, entity: SourcedEntityT):
        self._seen[str(entity.__reference__)] = entity

    def commit(self):
        for reference, entity in self._seen.items():
            events = list(entity.collect_events())
            self._events.append_to_stream(reference, events=events)
            self._capture_snapshot(entity, events=events)
        self._seen.clear()

    def _capture_snapshot(self, entity: SourcedEntityT, events: list[ISourcedEvent]):
        for i, event in enumerate(events):
            if self._interval and event.__entity_version__ % self._interval == 0:
                rehydrated_entity = self._rehydrate(
                    stream_name=str(entity.__reference__),
                    entity=entity,
                    from_version=0,
                    to_version=event.__entity_version__,
                )
                assert rehydrated_entity is not None
                self._snapshots.add_snapshot(str(entity.__reference__), rehydrated_entity.snapshot())

    def _rehydrate(
        self,
        stream_name: str,
        entity: t.Optional[SourcedEntityT],
        from_version: int,
        to_version: int,
    ) -> t.Optional[SourcedEntityT]:
        snapshot = self._snapshots.get_last_snapshot(stream_name)
        if snapshot is not None:
            entity = t.cast(SourcedEntityT, self._entity_cls.from_snapshot(snapshot))
            from_version = entity.__version__ + 1
        for event in self._events.get_from_stream(stream_name, from_version=from_version, to_version=to_version):
            entity = t.cast(SourcedEntityT, event.mutate(entity))
        return entity
