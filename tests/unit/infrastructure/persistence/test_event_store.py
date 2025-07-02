import uuid

import pytest

from pyddd.domain import SourcedDomainEvent
from pyddd.domain.abstractions import (
    SnapshotABC,
    Version,
)
from pyddd.infrastructure.persistence.abstractions import IEventStore
from pyddd.infrastructure.persistence.event_store import OptimisticConcurrencyError
from pyddd.infrastructure.persistence.event_store.in_memory import InMemoryEventStore


class ExampleEvent(SourcedDomainEvent, domain='test.event-store'):
    ...


class ExampleSnapshot(SnapshotABC):
    def __init__(self, state: bytes, reference: str, version: int):
        self._state = state
        self._reference = reference
        self._version = version

    @property
    def __state__(self) -> bytes:
        return self._state

    @property
    def __reference__(self):
        return self._reference

    @property
    def __version__(self) -> int:
        return self._version


class TestInMemoryEventStore:
    @pytest.fixture
    def mem(self):
        return dict()

    @pytest.fixture
    def store(self, mem):
        return InMemoryEventStore(memory=mem)

    @pytest.fixture
    def stream_name(self):
        return str(uuid.uuid4())

    def test_must_impl(self, store):
        assert isinstance(store, IEventStore)

    def test_could_create_stream(self, store, stream_name):
        assert list(store.get_from_stream(stream_name, 0, 100)) == []

    def test_could_append_to_stream(self, store, stream_name):
        events = [ExampleEvent(entity_reference=str(uuid.uuid4()), entity_version=Version(1))]
        store.append_to_stream(stream_name, events)
        assert store.get_from_stream(stream_name, 0, 1) == events

    def test_could_raise_error_if_conflict_of_version(self, store, stream_name):
        events = [ExampleEvent(entity_reference=str(uuid.uuid4()), entity_version=Version(1))]
        store.append_to_stream(stream_name, events)
        with pytest.raises(
                OptimisticConcurrencyError,
                match=f"Conflict version of stream {stream_name}. Expected version 2 found 1"
                ):
            store.append_to_stream(stream_name, events, expected_version=2)

    def test_could_add_and_get_snapshot(self, store, stream_name):
        store.add_snapshot(stream_name, ExampleSnapshot(state=b'{}', version=1, reference="123"))
        snapshot = store.get_last_snapshot(stream_name)
        assert snapshot.__state__ == b'{}'
        assert snapshot.__version__ == 1
        assert snapshot.__reference__ == "123"

    def test_could_get_none_if_not_created_snapshot(self, store, stream_name):
        assert store.get_last_snapshot(stream_name) is None
