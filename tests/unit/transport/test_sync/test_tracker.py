import dataclasses

import pytest
from pyddd.infrastructure.transport.asyncio.domain import (
    Notification,
)
from pyddd.infrastructure.transport.core.abstractions import (
    NotificationTrackerState,
    INotificationTrackerStrategy,
)
from pyddd.infrastructure.transport.core.tracker import NotificationTracker


class TestNotificationTracker:
    def test_last_recent_id_null_by_default(self):
        tracker = NotificationTrackerState(track_key="test:stream", last_recent_notification_id=None)
        assert tracker.last_recent_notification_id is None
        assert tracker.track_key == 'test:stream'


class TestNotificationTrackerEntity:
    @pytest.fixture
    def strategy(self):
        class CustomNotificationTrackerStrategy(INotificationTrackerStrategy):

            def track_most_recent_message(
                    self,
                    tracker: NotificationTrackerState,
                    *messages: Notification
            ) -> NotificationTrackerState:
                return dataclasses.replace(tracker, last_recent_notification_id='>')

            def create_tracker(self, track_key: str) -> NotificationTrackerState:
                return NotificationTrackerState(track_key=track_key, last_recent_notification_id='0')

        return CustomNotificationTrackerStrategy()

    def test_must_create_with_default_strategy(self):
        tracker = NotificationTracker(track_key='123')
        assert tracker.last_recent_notification_id is None

    def test_must_create_with_custom_strategy(self, strategy):
        tracker = NotificationTracker(track_key='123', track_strategy=strategy)
        assert tracker.last_recent_notification_id == '0'

    def test_must_track_with_custom_strategy(self, strategy):
        tracker = NotificationTracker(track_key='123', track_strategy=strategy)
        tracker.track_messages([])
        assert tracker.last_recent_notification_id == '>'
