import datetime as dt
import json
import uuid

from pyddd.domain.message import (
    Message,
)
from pyddd.domain.abstractions import (
    MessageType,
    IMessage,
)

from pyddd.infrastructure.transport.core.abstractions import (
    IEventFactory,
    IPublishingMessage,
)
from pyddd.infrastructure.transport.core.value_objects import PublishedEvent


class UniversalPublishingMessage(IPublishingMessage):
    def __init__(
        self,
        full_name: str,
        payload: dict,
        message_id: str = None,
    ):
        self._message_id = message_id or str(uuid.uuid4())
        self._full_name = full_name
        self._payload = payload

    @property
    def message_id(self) -> str:
        return self._message_id

    @property
    def name(self) -> str:
        return self._full_name

    @property
    def payload(self) -> dict:
        return self._payload


class UniversalEventFactory(IEventFactory):
    def build_event(self, notification: IPublishingMessage) -> Message:
        return Message(
            full_name=f"{notification.name.replace(':', '.')}",
            message_type=MessageType.EVENT,
            payload=notification.payload,
        )

    def build_publishing_message(self, message: IMessage) -> IPublishingMessage:
        return UniversalPublishingMessage(
            full_name=message.__topic__,
            message_id=message.__message_id__,
            payload=message.to_dict(),
        )


class PublishedEventFactory(IEventFactory):
    def build_event(self, notification: IPublishingMessage) -> Message:
        published_event = PublishedEvent(**notification.payload)
        return Message(
            full_name=published_event.full_event_name,
            message_id=published_event.message_id,
            message_type=MessageType.EVENT,
            payload=json.loads(published_event.payload),
            occurred_on=dt.datetime.fromtimestamp(float(published_event.timestamp)),
        )

    def build_publishing_message(self, message: IMessage) -> IPublishingMessage:
        return UniversalPublishingMessage(
            full_name=message.__topic__,
            message_id=message.__message_id__,
            payload=PublishedEvent(
                full_event_name=message.__topic__,
                message_id=message.__message_id__,
                payload=message.to_json(),
                timestamp=str(message.__timestamp__.timestamp()),
            ).__dict__,
        )
