import dataclasses

from pyddd.infrastructure.transport.core.abstractions import (
    INotificationTrackerStrategy,
    INotification,
)
from pyddd.infrastructure.transport.core.value_objects import NotificationTrackerState


class RedisStreamTrackerStrategy(INotificationTrackerStrategy):
    def create_tracker(self, track_key: str) -> NotificationTrackerState:
        tracker = NotificationTrackerState(track_key=track_key, last_recent_notification_id='0')
        return tracker

    def track_most_recent_message(
            self,
            tracker: NotificationTrackerState,
            *messages: INotification
            ) -> NotificationTrackerState:
        if not messages:
            last_notification_id = '>'
        else:
            last_notification_id = messages[-1].message_id
        return dataclasses.replace(tracker, last_recent_notification_id=last_notification_id)
