import dataclasses
import typing as t

from pyddd.domain.abstractions import ValueObject


@dataclasses.dataclass(frozen=True)
class PublishedEvent(ValueObject):
    full_event_name: str
    message_id: str
    payload: str
    timestamp: str


@dataclasses.dataclass(frozen=True)
class TrackerState(ValueObject):
    track_key: str
    last_recent_message_id: t.Optional[str]
