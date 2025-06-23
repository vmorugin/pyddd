import dataclasses

import pytest
from pyddd.infrastructure.transport.asyncio.domain import (
    PublishedMessage,
)
from pyddd.infrastructure.transport.core.abstractions import (
    ITrackerStrategy,
)
from pyddd.infrastructure.transport.core.value_objects import TrackerState
from pyddd.infrastructure.transport.core.tracker import Tracker


class TestNotificationTracker:
    def test_last_recent_id_null_by_default(self):
        tracker = TrackerState(track_key="test:stream", last_recent_message_id=None)
        assert tracker.last_recent_message_id is None
        assert tracker.track_key == "test:stream"


class TestNotificationTrackerEntity:
    @pytest.fixture
    def strategy(self):
        class CustomTrackerStrategy(ITrackerStrategy):
            def track_most_recent_message(
                self, tracker: TrackerState, *messages: PublishedMessage
            ) -> TrackerState:
                return dataclasses.replace(tracker, last_recent_message_id=">")

            def create_tracker(self, track_key: str) -> TrackerState:
                return TrackerState(track_key=track_key, last_recent_message_id="0")

        return CustomTrackerStrategy()

    def test_must_create_with_default_strategy(self):
        tracker = Tracker(track_key="123")
        assert tracker.last_recent_message_id is None

    def test_must_create_with_custom_strategy(self, strategy):
        tracker = Tracker(track_key="123", track_strategy=strategy)
        assert tracker.last_recent_message_id == "0"

    def test_must_track_with_custom_strategy(self, strategy):
        tracker = Tracker(track_key="123", track_strategy=strategy)
        tracker.track_messages([])
        assert tracker.last_recent_message_id == ">"
