import dataclasses
import typing as t

from pyddd.infrastructure.transport.core.abstractions import (
    INotification,
    INotificationTracker,
    INotificationTrackerStrategy,
)
from pyddd.infrastructure.transport.core.value_objects import NotificationTrackerState


class DefaultNotificationTrackerStrategy(INotificationTrackerStrategy):

    def create_tracker(self, track_key: str) -> NotificationTrackerState:
        return NotificationTrackerState(track_key=track_key, last_recent_notification_id=None)

    def track_most_recent_message(
            self,
            tracker: NotificationTrackerState,
            *messages: INotification
    ) -> NotificationTrackerState:
        if not messages:
            return tracker
        last_message = messages[-1]
        return dataclasses.replace(tracker, last_recent_notification_id=last_message.message_id)


class NotificationTracker(INotificationTracker):
    def __init__(
            self,
            track_key: str,
            track_strategy: INotificationTrackerStrategy = DefaultNotificationTrackerStrategy()
    ):
        self._strategy = track_strategy
        self._tracker = track_strategy.create_tracker(track_key)

    @property
    def last_recent_notification_id(self):
        return self._tracker.last_recent_notification_id

    def track_messages(self, messages: t.Iterable[INotification]):
        tracker = self._strategy.track_most_recent_message(self._tracker, *messages)
        self._tracker = tracker
