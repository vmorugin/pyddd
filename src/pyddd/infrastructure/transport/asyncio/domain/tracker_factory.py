from pyddd.infrastructure.transport.asyncio.domain.abstractions import (
    INotificationTrackerFactory,
    INotificationTracker,
    INotificationTrackerStrategy,
)
from pyddd.infrastructure.transport.asyncio.domain.tracker import (
    NotificationTracker,
)


class NotificationTrackerFactory(INotificationTrackerFactory):
    def __init__(self, strategy: INotificationTrackerStrategy):
        self._strategy = strategy

    def create_tracker(self, track_key: str) -> INotificationTracker:
        return NotificationTracker(track_key=track_key, track_strategy=self._strategy)
