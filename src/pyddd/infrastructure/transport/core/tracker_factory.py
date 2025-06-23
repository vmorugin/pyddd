from pyddd.infrastructure.transport.core.abstractions import (
    ITrackerFactory,
    ITrackerStrategy,
    ITracker,
)
from pyddd.infrastructure.transport.core.tracker import Tracker


class TrackerFactory(ITrackerFactory):
    def __init__(self, strategy: ITrackerStrategy):
        self._strategy = strategy

    def create_tracker(self, track_key: str) -> ITracker:
        return Tracker(track_key=track_key, track_strategy=self._strategy)
