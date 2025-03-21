from pyddd.infrastructure.transport.core.abstractions import (
    INotificationTrackerFactory,
    INotificationTrackerStrategy,
    INotificationTracker,
)
from pyddd.infrastructure.transport.core.tracker import NotificationTracker


class NotificationTrackerFactory(INotificationTrackerFactory):
    def __init__(self, strategy: INotificationTrackerStrategy):
        self._strategy = strategy

    def create_tracker(self, track_key: str) -> INotificationTracker:
        return NotificationTracker(track_key=track_key, track_strategy=self._strategy)
