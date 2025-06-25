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
from pyddd.infrastructure.persistence.abstractions import IStoredEvent


@dataclass(kw_only=True, eq=True, frozen=True, slots=True)
class StoredEvent(IStoredEvent):
    event_id: int
    body: str
    full_name: str
    occurred_on: dt.datetime
    version: int


class Converter:
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
