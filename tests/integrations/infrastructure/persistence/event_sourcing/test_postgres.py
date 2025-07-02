import os
import uuid
from contextlib import suppress

import psycopg
import pytest
from psycopg.errors import DuplicateDatabase

from pyddd.domain import SourcedDomainEvent
from pyddd.domain.abstractions import Version
from pyddd.infrastructure.persistence.abstractions import IEventStore
from pyddd.infrastructure.persistence.event_store import OptimisticConcurrencyError
from pyddd.infrastructure.persistence.event_store.postgres import (
    PostgresEventStore,
    PostgresDatastore,
    PostgresEventRecorder,
    PostgresSnapshotRecorder,
    IEventRecorder,
    ISnapshotRecorder,
)
from unit.infrastructure.persistence.test_event_store import ExampleSnapshot


@pytest.fixture
def postgres_config():
    return {
        "dbname": os.getenv("POSTGRES_DB", "eventsourcing"),
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "username": os.getenv("POSTGRES_USERNAME", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    }


@pytest.fixture
def root_conn(postgres_config):
    return psycopg.connect(
        dbname="postgres",
        host=postgres_config["host"],
        port=postgres_config["port"],
        user=postgres_config["username"],
        password=postgres_config["password"],
        autocommit=True,
    )


@pytest.fixture
def pg_conn(postgres_config):
    return psycopg.connect(
        dbname=postgres_config["dbname"],
        host=postgres_config["host"],
        port=postgres_config["port"],
        user=postgres_config["username"],
        password=postgres_config["password"],
        autocommit=True,
    )


@pytest.fixture
def prepare_database(postgres_config, root_conn):
    with suppress(DuplicateDatabase):
        root_conn.execute("CREATE DATABASE {database};".format(database=postgres_config["dbname"]))


@pytest.fixture
def datastore(postgres_config, prepare_database, pg_conn):
    datastore = PostgresDatastore(
        dbname=postgres_config["dbname"],
        host=postgres_config["host"],
        port=postgres_config["port"],
        user=postgres_config["username"],
        password=postgres_config["password"],
        schema="public",
    )
    yield datastore
    pg_conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")


class TestEventRecorder:
    @pytest.fixture
    def domain_name(self):
        return str(uuid.uuid4())

    @pytest.fixture
    def recorder(self, datastore, domain_name):
        return PostgresEventRecorder(datastore, events_table_name=domain_name + "_events")

    def test_must_impl(self, recorder):
        assert isinstance(recorder, IEventRecorder)

    def test_max_table_name_len_63_chars(self):
        long_domain = "a" * 64
        with pytest.raises(ValueError, match=f"Identifier too long: {long_domain}. Max length is 63 characters."):
            PostgresEventRecorder(..., events_table_name=long_domain)

    def test_could_create_table(self, datastore, pg_conn):
        recorder = PostgresEventRecorder(datastore=datastore, events_table_name="test_events")
        recorder.create_table()
        pg_conn.execute("SELECT 1 FROM test_events;")


class TestSnapshotRecorder:
    @pytest.fixture
    def domain_name(self):
        return str(uuid.uuid4())

    @pytest.fixture
    def recorder(self, datastore, domain_name):
        return PostgresSnapshotRecorder(datastore, snapshots_table_name=domain_name + "_snapshots")

    def test_must_impl(self, recorder):
        assert isinstance(recorder, ISnapshotRecorder)

    def test_max_table_name_len_63_chars(self):
        long_domain = "a" * 64
        with pytest.raises(ValueError, match=f"Identifier too long: {long_domain}. Max length is 63 characters."):
            PostgresSnapshotRecorder(..., snapshots_table_name=long_domain)


class ExampleEvent(SourcedDomainEvent, domain="test.event-sourcing-pg"): ...


class TestEventStore:
    @pytest.fixture
    def stream_name(self):
        return str(uuid.uuid4())

    @pytest.fixture
    def domain_name(self):
        return str(uuid.uuid4()).replace("-", "_")

    @pytest.fixture
    def events_recorder(self, datastore, domain_name):
        return PostgresEventRecorder(datastore, events_table_name=domain_name + "_events")

    @pytest.fixture
    def snapshots_recorder(self, datastore, domain_name):
        return PostgresSnapshotRecorder(datastore, snapshots_table_name=domain_name + "_snapshots")

    @pytest.fixture
    def store(self, events_recorder, snapshots_recorder):
        store = PostgresEventStore(events_recorder=events_recorder, snapshots_recorder=snapshots_recorder)
        events_recorder.create_table()
        snapshots_recorder.create_table()
        yield store

    def test_must_impl(self, store):
        assert isinstance(store, IEventStore)

    def test_could_get_empty_stream(self, store, stream_name):
        assert list(store.get_from_stream(stream_name, 0, 100)) == []

    def test_could_append_to_stream(self, store, stream_name):
        event = ExampleEvent(entity_reference=stream_name, entity_version=Version(1))
        store.append_to_stream(stream_name, [event])
        events = list(store.get_from_stream(stream_name, 0, 1))
        assert len(events) == 1
        db_event = events.pop()
        assert db_event.__entity_reference__ == event.__entity_reference__
        assert db_event.__entity_version__ == event.__entity_version__

    def test_could_raise_error_if_conflict_of_version(self, store, stream_name):
        events = [ExampleEvent(entity_reference=stream_name, entity_version=Version(1))]
        store.append_to_stream(stream_name, events)
        with pytest.raises(OptimisticConcurrencyError, match=f"Conflict version of stream {stream_name}."):
            store.append_to_stream(stream_name, events, expected_version=2)

    def test_could_add_and_get_snapshot(self, store, stream_name):
        store.add_snapshot(stream_name, ExampleSnapshot(state=b"{}", version=1, reference=stream_name))
        snapshot = store.get_last_snapshot(stream_name)
        assert snapshot.__state__ == b"{}"
        assert snapshot.__entity_version__ == 1
        assert snapshot.__entity_reference__ == stream_name

    def test_could_get_none_if_not_created_snapshot(self, store, stream_name):
        assert store.get_last_snapshot(stream_name) is None
