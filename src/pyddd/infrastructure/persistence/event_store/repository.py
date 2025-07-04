import sys
import typing as t
from pyddd.domain.abstractions import (
    IdType,
    ISourcedEvent,
    SnapshotProtocol,
)
from pyddd.domain.event_sourcing import SourcedEntityT
from pyddd.infrastructure.persistence.abstractions import (
    IESRepository,
    IEventStore,
    ISnapshotStore,
)

class NullSnapshotStore(ISnapshotStore):
    def add_snapshot(self, stream_name: str, snapshot: SnapshotProtocol):
        raise NotImplementedError("Can not add snapshot using NullSnapshotStore")

    def get_last_snapshot(self, stream_name: str) -> t.Optional[SnapshotProtocol]:
        pass


class EventSourcedRepository(IESRepository[SourcedEntityT]):
    def __init__(
        self,
        event_store: IEventStore,
        entity_cls: type[SourcedEntityT],
        snapshot_store: ISnapshotStore = NullSnapshotStore(),
        snapshot_interval: int = 0,
    ):
        self._events = event_store
        self._snapshots = snapshot_store
        self._interval = snapshot_interval
        self._entity_cls = entity_cls
        self._seen: dict[str, SourcedEntityT] = {}

    def add(self, entity: SourcedEntityT):
        self._seen[str(entity.__reference__)] = entity

    def find_by(self, entity_id: IdType) -> t.Optional[SourcedEntityT]:
        to_version = sys.maxsize
        from_version = 0
        entity: t.Optional[SourcedEntityT] = None

        latest = self._snapshots.get_last_snapshot(str(entity_id))
        if latest is not None:
            entity = t.cast(SourcedEntityT, self._entity_cls.from_snapshot(latest))
            from_version = entity.__version__ + 1

        stream = self._events.get_from_stream(str(entity_id), from_version=from_version, to_version=to_version)
        for event in stream:
            entity = t.cast(SourcedEntityT, event.mutate(entity))
        if entity:
            self._seen[str(entity.__reference__)] = entity
        return entity

    def commit(self):
        for reference, entity in self._seen.items():
            events = list(entity.collect_events())
            self._events.append_to_stream(reference, events)
            self._capture_snapshot(entity, events=events)
        self._seen.clear()

    def _capture_snapshot(self, entity: SourcedEntityT, events: list[ISourcedEvent]):
        last_snapshot: t.Optional[SnapshotProtocol] = None
        for i, event in enumerate(events):
            if self._interval and event.__entity_version__ % self._interval == 0:
                last_snapshot = last_snapshot or self._snapshots.get_last_snapshot(str(entity.__reference__))
                if last_snapshot:
                    entity = self._rebuild_entity(
                        entity=t.cast(SourcedEntityT, self._entity_cls.from_snapshot(last_snapshot)),
                        from_version=last_snapshot.__entity_version__ + 1,
                        to_version=event.__entity_version__,
                    )
                last_snapshot = entity.snapshot()
                self._snapshots.add_snapshot(str(entity.__reference__), last_snapshot)

    def _rebuild_entity(self, entity: SourcedEntityT, from_version: int, to_version: int) -> SourcedEntityT:
        for event in self._events.get_from_stream(
            str(entity.__reference__), from_version=from_version, to_version=to_version
        ):
            entity = t.cast(SourcedEntityT, event.mutate(entity))
        return entity
