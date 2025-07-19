import typing as t

from pyddd.domain.abstractions import (
    SnapshotProtocol,
    IESEvent,
)
from pyddd.infrastructure.persistence.abstractions import (
    IEventStore,
    ISnapshotStore,
)
from pyddd.infrastructure.persistence.event_store import OptimisticConcurrencyError


class InMemoryStore(IEventStore, ISnapshotStore):
    def __init__(
        self,
        events: dict[str, dict[int, IESEvent]] = None,
        snapshots: dict[str, list[SnapshotProtocol]] = None,
    ):
        self._events = events if events is not None else {}
        self._snapshots = snapshots if snapshots is not None else {}

    def append_to_stream(self, stream_name: str, events: t.Iterable[IESEvent]):
        stream = self._get_or_create_event_stream(stream_name)
        for event in events:
            if event.__entity_version__ in stream:
                raise OptimisticConcurrencyError(
                    f"Conflict version of stream {stream_name}. Version {event.__entity_version__} exists"
                )
            stream[event.__entity_version__] = event

    def get_stream(self, stream_name: str, from_version: int, to_version: int) -> t.Iterable[IESEvent]:
        stream = self._get_or_create_event_stream(stream_name)
        return [event for version, event in stream.items() if from_version <= version <= to_version]

    def add_snapshot(self, stream_name: str, snapshot: SnapshotProtocol):
        stream = self._get_or_create_snapshot_stream(stream_name)
        stream.append(snapshot)

    def get_last_snapshot(self, stream_name: str) -> t.Optional[SnapshotProtocol]:
        stream = self._get_or_create_snapshot_stream(stream_name)
        if stream:
            return stream[-1]
        return None

    def _get_or_create_event_stream(self, stream_name: str) -> dict[int, IESEvent]:
        event_stream_name = self._get_event_stream_name(stream_name)
        stream = self._events.get(event_stream_name)
        if stream is None:
            stream = {}
            self._events[event_stream_name] = stream
        return stream

    def _get_or_create_snapshot_stream(self, stream_name: str) -> list[SnapshotProtocol]:
        snapshot_stream_name = self._get_event_stream_name(stream_name)
        stream = self._snapshots.get(snapshot_stream_name)
        if stream is None:
            stream = []
            self._snapshots[snapshot_stream_name] = stream
        return stream

    @staticmethod
    def _get_event_stream_name(stream_name: str) -> str:
        return f"{stream_name}-events"

    @staticmethod
    def _get_snapshot_stream_name(stream_name: str) -> str:
        return f"{stream_name}-snapshots"
