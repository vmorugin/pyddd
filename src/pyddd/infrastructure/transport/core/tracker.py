import dataclasses
import typing as t

from pyddd.infrastructure.transport.core.abstractions import (
    IPublishedMessage,
    ITracker,
    ITrackerStrategy,
)
from pyddd.infrastructure.transport.core.value_objects import TrackerState


class DefaultTrackerStrategy(ITrackerStrategy):
    def create_tracker(self, track_key: str) -> TrackerState:
        return TrackerState(track_key=track_key, last_recent_message_id=None)

    def track_most_recent_message(self, tracker: TrackerState, *messages: IPublishedMessage) -> TrackerState:
        if not messages:
            return tracker
        last_message = messages[-1]
        return dataclasses.replace(tracker, last_recent_message_id=last_message.message_id)


class Tracker(ITracker):
    def __init__(
        self,
        track_key: str,
        track_strategy: ITrackerStrategy = DefaultTrackerStrategy(),
    ):
        self._strategy = track_strategy
        self._tracker = track_strategy.create_tracker(track_key)

    @property
    def last_recent_message_id(self):
        return self._tracker.last_recent_message_id

    def track_messages(self, messages: t.Iterable[IPublishedMessage]):
        tracker = self._strategy.track_most_recent_message(self._tracker, *messages)
        self._tracker = tracker
