import abc
import datetime as dt
import json
from dataclasses import dataclass

from pyddd.domain.abstractions import (
    IEvent,
    IMessage,
    MessageType,
    Version,
)
from pyddd.domain.message import Message


@dataclass(kw_only=True, eq=True, frozen=True, slots=True)
class StoredEvent:
    event_id: int
    body: str
    full_name: str
    occurred_on: dt.datetime
    version: int


class IEventStore(abc.ABC):
    @abc.abstractmethod
    def stored_events_between(self, low_stored_event_id: int, high_stored_event_id: int) -> list[StoredEvent]: ...

    @abc.abstractmethod
    def stored_events_since(self, stored_event_id: int) -> list[StoredEvent]: ...

    @abc.abstractmethod
    def append(self, event: IEvent) -> StoredEvent: ...

    @abc.abstractmethod
    def count_stored_events(self) -> int: ...


class EventStoreTranslator:
    @classmethod
    def domain_event_to_stored_event(cls, domain_event: IEvent, stored_event_id: int) -> StoredEvent:
        return StoredEvent(
            occurred_on=domain_event.__timestamp__,
            full_name=domain_event.__topic__,
            version=domain_event.__version__,
            event_id=stored_event_id,
            body=domain_event.to_json(),
        )

    @classmethod
    def stored_event_to_domain_event(cls, stored_event: StoredEvent) -> IMessage:
        return Message(
            full_name=stored_event.full_name,
            message_type=MessageType.EVENT,
            payload=json.loads(stored_event.body),
            occurred_on=stored_event.occurred_on,
            event_version=Version(stored_event.version),
        )
