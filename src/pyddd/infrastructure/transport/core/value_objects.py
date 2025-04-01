import dataclasses
import typing as t

from pyddd.domain.entity import ValueObject


@dataclasses.dataclass(frozen=True)
class PublishedEvent(ValueObject):
    full_event_name: str
    message_id: str
    payload: str
    timestamp: str


@dataclasses.dataclass(frozen=True)
class NotificationTrackerState(ValueObject):
    track_key: str
    last_recent_notification_id: t.Optional[str]
