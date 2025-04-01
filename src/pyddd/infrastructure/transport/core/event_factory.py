import datetime as dt
import json

from pyddd.domain.message import (
    Message,
    MessageType,
)

from pyddd.infrastructure.transport.core.abstractions import (
    IEventFactory,
    INotification,
)
from pyddd.infrastructure.transport.core.value_objects import PublishedEvent


class UniversalEventFactory(IEventFactory):
    def build_event(self, message: INotification) -> Message:
        return Message(
            full_name=f"{message.name.replace(':', '.')}",
            message_type=MessageType.EVENT,
            payload=message.payload,
        )


class PublishedEventFactory(IEventFactory):
    def build_event(self, message: INotification) -> Message:
        published_event = PublishedEvent(**message.payload)
        return Message(
            full_name=published_event.full_event_name,
            message_id=published_event.message_id,
            message_type=MessageType.EVENT,
            payload=json.loads(published_event.payload),
            occurred_on=dt.datetime.fromtimestamp(float(published_event.timestamp))
        )
