import typing as t

from pyddd.domain.abstractions import (
    ISourcedEvent,
    SnapshotProtocol,
)
from pyddd.infrastructure.persistence.abstractions import (
    IEventStore,
    ISnapshotStore,
)
from pyddd.infrastructure.persistence.event_store import OptimisticConcurrencyError


class InMemoryStore(IEventStore, ISnapshotStore):
    def __init__(
        self,
        events: dict[str, list[ISourcedEvent]] = None,
        snapshots: dict[str, list[SnapshotProtocol]] = None,
    ):
        self._events: dict[str, list[ISourcedEvent]] = events if events is not None else {}
        self._snapshots: dict[str, list[SnapshotProtocol]] = snapshots if snapshots is not None else {}

    def append_to_stream(
        self, stream_name: str, events: t.Iterable[ISourcedEvent], expected_version: t.Optional[int] = None
    ):
        stream = self._get_or_create_event_stream(stream_name)
        if expected_version and stream:
            last_version = stream[-1].__entity_version__
            if last_version != expected_version:
                raise OptimisticConcurrencyError(
                    f"Conflict version of stream {stream_name}. "
                    f"Expected version {expected_version} found {last_version}"
                )
        stream.extend(events)

    def get_from_stream(self, stream_name: str, from_version: int, to_version: int) -> t.Iterable[ISourcedEvent]:
        stream = self._get_or_create_event_stream(stream_name)
        return [event for event in stream if from_version <= event.__entity_version__ <= to_version]

    def add_snapshot(self, stream_name: str, snapshot: SnapshotProtocol):
        stream = self._get_or_create_snapshot_stream(stream_name)
        stream.append(snapshot)

    def get_last_snapshot(self, stream_name: str) -> t.Optional[SnapshotProtocol]:
        stream = self._get_or_create_snapshot_stream(stream_name)
        if stream:
            return stream[-1]
        return None

    def _get_or_create_event_stream(self, stream_name: str) -> list[ISourcedEvent]:
        event_stream_name = self._get_event_stream_name(stream_name)
        stream = self._events.get(event_stream_name)
        if stream is None:
            stream = []
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
