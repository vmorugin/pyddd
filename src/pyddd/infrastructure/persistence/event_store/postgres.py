import abc
import contextlib
import json
import typing as t
import datetime as dt
from contextlib import contextmanager

import psycopg_pool
from psycopg import (
    Connection,
    Cursor,
)
from psycopg.errors import UniqueViolation
from psycopg.rows import (
    dict_row,
    DictRow,
)
from psycopg.sql import (
    SQL,
    Identifier,
)

from pyddd.domain.abstractions import (
    ISourcedEvent,
)
from pyddd.domain.event_sourcing import SnapshotABC
from pyddd.domain.message import get_message_class
from pyddd.infrastructure.persistence.abstractions import IEventStore
from pyddd.infrastructure.persistence.event_store import OptimisticConcurrencyError


class ConnectionPool(psycopg_pool.ConnectionPool[t.Any]):
    def __init__(
        self,
        *args,
        get_password_func: t.Callable[[], str] | None = None,
        **kwargs: t.Any,
    ) -> None:
        self.get_password_func = get_password_func
        super().__init__(*args, **kwargs)

    def _connect(self, timeout: float | None = None) -> Connection[t.Any]:
        if self.get_password_func:
            self.kwargs["password"] = self.get_password_func()
        return super()._connect(timeout=timeout)


class PostgresDatastore:
    def __init__(
        self,
        dbname: str,
        host: str = "localhost",
        port: str | int = "5432",
        user: str = "postgres",
        password: str = "postgres",
        *,
        connect_timeout: float = 5.0,
        idle_in_transaction_session_timeout: float = 0,
        pool_size: int = 1,
        max_overflow: int = 0,
        max_waiting: int = 0,
        conn_max_age: float = 60 * 60.0,
        pre_ping: bool = False,
        schema: str = "public",
        pool_open_timeout: float | None = None,
        get_password_func: t.Callable[[], str] | None = None,
        enable_db_functions: bool = False,
    ):
        self._idle_in_transaction_session_timeout = idle_in_transaction_session_timeout
        self._pre_ping = pre_ping
        self._pool_open_timeout = pool_open_timeout
        self._schema = schema.strip()
        self._enable_db_functions = enable_db_functions
        self._pool = ConnectionPool(
            get_password_func=get_password_func,
            connection_class=Connection[DictRow],
            kwargs={
                "dbname": dbname,
                "host": host,
                "port": port,
                "user": user,
                "password": password,
                "row_factory": dict_row,
            },
            min_size=pool_size,
            max_size=pool_size + max_overflow,
            open=False,
            configure=self.after_connect_func(),
            timeout=connect_timeout,
            max_waiting=max_waiting,
            max_lifetime=conn_max_age,
            check=ConnectionPool.check_connection if pre_ping else None,
        )

    @property
    def schema(self):
        return self._schema

    def after_connect_func(self) -> t.Callable[[Connection[t.Any]], None]:
        set_idle_in_transaction_session_timeout_statement = SQL(
            "SET idle_in_transaction_session_timeout = '{0}ms'"
        ).format(int(self._idle_in_transaction_session_timeout * 1000))

        # Avoid passing a bound method to the pool,
        # to avoid creating a circular ref to self.
        def after_connect(conn: Connection[DictRow]) -> None:
            conn.autocommit = True

            conn.cursor().execute(set_idle_in_transaction_session_timeout_statement)

        return after_connect

    @contextmanager
    def get_connection(self) -> t.Iterator[Connection[DictRow]]:
        try:
            wait = self._pool_open_timeout is not None
            timeout = self._pool_open_timeout or 30.0
            self._pool.open(wait, timeout)

            with self._pool.connection() as conn:
                yield conn
        except Exception:
            raise

    @contextmanager
    def cursor(self) -> t.Iterator[Cursor[DictRow]]:
        with self.get_connection() as conn:
            yield conn.cursor()

    @contextmanager
    def transaction(self, *, commit: bool = False) -> t.Iterator[Cursor[DictRow]]:
        with self.get_connection() as conn, conn.transaction(force_rollback=not commit):
            yield conn.cursor()

    def close(self) -> None:
        with contextlib.suppress(AttributeError):
            self._pool.close()

    def __del__(self) -> None:
        self.close()


MAX_IDENTIFIER_LEN = 63


class IRecorder(abc.ABC):
    @abc.abstractmethod
    def create_table(self) -> None:
        """
        Create the necessary table for recording events or snapshots.
        """


class IEventRecorder(IRecorder, abc.ABC):
    @abc.abstractmethod
    def insert_events(self, stream_name: str, events: t.Iterable[ISourcedEvent]) -> None:
        """
        Insert an event into the event store.
        """

    @abc.abstractmethod
    def select_events(self, stream_name: str, from_version: int, to_version: int) -> t.Iterable[ISourcedEvent]:
        """
        Select events from the event store for a specific entity.
        """


class ISnapshotRecorder(IRecorder, abc.ABC):
    @abc.abstractmethod
    def insert_snapshot(self, stream_name: str, snapshot: SnapshotABC) -> None:
        """
        Insert a snapshot into the snapshot store.
        """

    @abc.abstractmethod
    def select_latest(self, stream_name: str) -> t.Optional[SnapshotABC]:
        """
        Select the last snapshot for a specific entity.
        """


class PostgresEventRecorder(IEventRecorder):
    def __init__(self, datastore: PostgresDatastore, events_table_name: str):
        self._check_identifier_length(events_table_name)
        self._datastore = datastore
        self._events_table = events_table_name

    @staticmethod
    def _check_identifier_length(table_name: str) -> None:
        if len(table_name) > MAX_IDENTIFIER_LEN:
            msg = f"Identifier too long: {table_name}. Max length is {MAX_IDENTIFIER_LEN} characters."
            raise ValueError(msg)

    def insert_events(self, stream_name: str, events: t.Iterable[ISourcedEvent]) -> None:
        with self._datastore.cursor() as cur:
            cur.executemany(
                Statements.INSERT_EVENTS.format(
                    schema=Identifier(self._datastore.schema),
                    table=Identifier(self._events_table),
                ),
                (Converter.event_to_dict(event) for event in events),
            )

    def select_events(self, stream_name: str, from_version: int, to_version: int) -> t.Iterable[ISourcedEvent]:
        with self._datastore.cursor() as cur:
            cur.execute(
                Statements.SELECT_EVENTS.format(
                    schema=Identifier(self._datastore.schema),
                    table=Identifier(self._events_table),
                ),
                {"entity_id": stream_name, "from_version": from_version, "to_version": to_version},
            )
            yield from (Converter.event_from_dict(row) for row in cur)

    def create_table(self) -> None:
        with self._datastore.get_connection() as conn:
            conn.execute(
                Statements.CREATE_EVENT_TABLE.format(
                    schema=Identifier(self._datastore.schema),
                    table=Identifier(self._events_table),
                )
            )


class NullSnapshotRecorder(ISnapshotRecorder):
    def insert_snapshot(self, stream_name: str, snapshot: SnapshotABC) -> None:
        raise NotImplementedError("Not implemented for NullSnapshotRecorder")

    def select_latest(self, stream_name: str) -> t.Optional[SnapshotABC]:
        raise NotImplementedError("Not implemented for NullSnapshotRecorder")

    def create_table(self) -> None:
        pass


class PostgresSnapshotRecorder(ISnapshotRecorder):
    def __init__(self, datastore: PostgresDatastore, snapshots_table_name: str):
        self._check_identifier_length(snapshots_table_name)
        self._datastore = datastore
        self._snapshots_table = snapshots_table_name

    @staticmethod
    def _check_identifier_length(table_name: str) -> None:
        if len(table_name) > MAX_IDENTIFIER_LEN:
            msg = f"Identifier too long: {table_name}. Max length is {MAX_IDENTIFIER_LEN} characters."
            raise ValueError(msg)

    def insert_snapshot(self, stream_name: str, snapshot: SnapshotABC) -> None:
        with self._datastore.get_connection() as conn:
            conn.execute(
                Statements.INSERT_SNAPSHOT.format(
                    schema=Identifier(self._datastore.schema),
                    table=Identifier(self._snapshots_table),
                ),
                Converter.snapshot_to_dict(snapshot),
            )

    def select_latest(self, stream_name: str) -> t.Optional[SnapshotABC]:
        with self._datastore.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    Statements.SELECT_LATEST_SNAPSHOT.format(
                        schema=Identifier(self._datastore.schema),
                        table=Identifier(self._snapshots_table),
                    ),
                    {"entity_id": stream_name},
                )
                row: t.Optional[DictRow] = cur.fetchone()
                if row:
                    return Converter.snapshot_from_dict(row)
                return None

    def create_table(self) -> None:
        with self._datastore.get_connection() as conn:
            conn.execute(
                Statements.CREATE_SNAPSHOT_TABLE.format(
                    schema=Identifier(self._datastore.schema),
                    table=Identifier(self._snapshots_table),
                )
            )


class PostgresEventStore(IEventStore):
    def __init__(
        self,
        events_recorder: IEventRecorder,
        snapshots_recorder: ISnapshotRecorder = NullSnapshotRecorder(),
    ):
        self._events = events_recorder
        self._snapshots = snapshots_recorder

    def append_to_stream(
        self, stream_name: str, events: t.Iterable[ISourcedEvent], expected_version: t.Optional[int] = None
    ):
        try:
            self._events.insert_events(stream_name=stream_name, events=events)
        except UniqueViolation:
            raise OptimisticConcurrencyError(f"Conflict version of stream {stream_name}.")

    def get_from_stream(self, stream_name: str, from_version: int, to_version: int) -> t.Iterable[ISourcedEvent]:
        return self._events.select_events(stream_name=stream_name, from_version=from_version, to_version=to_version)

    def add_snapshot(self, stream_name: str, snapshot: SnapshotABC):
        self._snapshots.insert_snapshot(stream_name, snapshot)

    def get_last_snapshot(self, stream_name: str) -> t.Optional[SnapshotABC]:
        return self._snapshots.select_latest(stream_name)


class Converter:
    @classmethod
    def event_to_dict(cls, event: ISourcedEvent) -> dict:
        return {
            "entity_id": event.__entity_reference__,
            "entity_version": event.__entity_version__,
            "correlation_id": event.__message_id__,
            "topic": event.__topic__,
            "state": event.to_json(),
            "created_at": event.__timestamp__,
        }

    @classmethod
    def event_from_dict(cls, data: dict) -> ISourcedEvent:
        entity_type = get_message_class(data["topic"])
        event = entity_type.load(
            payload=json.loads(data["state"]),
            entity_reference=data["entity_id"],
            entity_version=data["entity_version"],
            message_id=data["correlation_id"],
            timestamp=data["created_at"],
        )
        assert isinstance(event, ISourcedEvent)
        return event

    @classmethod
    def snapshot_to_dict(cls, snapshot: SnapshotABC) -> dict:
        return {
            "entity_id": snapshot.__entity_reference__,
            "entity_version": snapshot.__entity_version__,
            "state": snapshot.__state__,
            "topic": snapshot.__topic__,
            "created_at": dt.datetime.now(dt.timezone.utc),
        }

    @classmethod
    def snapshot_from_dict(cls, data: dict) -> SnapshotABC:
        entity_type = SnapshotABC.get_by_name(data["topic"])
        snapshot = entity_type.load(
            state=data["state"],
            entity_reference=data["entity_id"],
            entity_version=data["entity_version"],
        )
        assert isinstance(snapshot, SnapshotABC)
        return snapshot


class Statements:
    CREATE_EVENT_TABLE = SQL(
        """
        CREATE TABLE IF NOT EXISTS {schema}.{table} (
            entity_id VARCHAR NOT NULL,
            entity_version BIGINT NOT NULL,
            topic TEXT,
            state BYTEA,
            notification_id BIGSERIAL,
            correlation_id UUID NOT NULL,
            created_at TIMESTAMPTZ,
            PRIMARY KEY (entity_id, entity_version)
        ) WITH (
                    autovacuum_enabled = true,
                    autovacuum_vacuum_threshold = 100000000,
                    autovacuum_vacuum_scale_factor = 0.5,
                    autovacuum_analyze_threshold = 1000,
                    autovacuum_analyze_scale_factor = 0.01
                );
        
        CREATE UNIQUE INDEX IF NOT EXISTS notification_id_idx ON {schema}.{table} (notification_id);
        CREATE UNIQUE INDEX IF NOT EXISTS created_at_idx ON {schema}.{table} (created_at);
        """
    )

    CREATE_SNAPSHOT_TABLE = SQL(
        """
        CREATE TABLE IF NOT EXISTS {schema}.{table} (
            entity_id VARCHAR NOT NULL,
            entity_version BIGINT NOT NULL,
            topic TEXT NOT NULL,
            state BYTEA NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (entity_id, entity_version)
        ) WITH (
                    autovacuum_enabled = true,
                    autovacuum_vacuum_threshold = 100000000,
                    autovacuum_vacuum_scale_factor = 0.5,
                    autovacuum_analyze_threshold = 1000,
                    autovacuum_analyze_scale_factor = 0.01
                );
        """
    )

    INSERT_EVENTS = SQL(
        """
        INSERT INTO {schema}.{table} 
        (entity_id, entity_version, correlation_id, topic, state, created_at)
        VALUES (%(entity_id)s, %(entity_version)s, %(correlation_id)s, %(topic)s, %(state)s, %(created_at)s)
        """
    )

    SELECT_EVENTS = SQL(
        """
        SELECT entity_id, entity_version, topic, state, created_at, correlation_id
        FROM {schema}.{table}
        WHERE entity_id = %(entity_id)s AND entity_version BETWEEN %(from_version)s AND %(to_version)s
        """
    )

    INSERT_SNAPSHOT = SQL(
        """
        INSERT INTO {schema}.{table} 
        (entity_id, entity_version, topic, state, created_at)
        VALUES (%(entity_id)s, %(entity_version)s, %(topic)s, %(state)s, %(created_at)s)
        """
    )

    SELECT_LATEST_SNAPSHOT = SQL(
        """
        SELECT entity_id, entity_version, state, topic, created_at
        FROM {schema}.{table}
        WHERE entity_id = %(entity_id)s
        ORDER BY entity_version DESC
        LIMIT 1
        """
    )
