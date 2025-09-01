import uuid

import pytest

from pyddd.infrastructure.transport.sync.redis.stream_group.consumer import (
    GroupStreamHandler,
    RedisStreamTrackerStrategy,
)
from pyddd.infrastructure.transport.core.tracker_factory import (
    TrackerFactory,
)


@pytest.fixture
def redis(redis_container):
    return redis_container.get_client()


@pytest.fixture
def group_name():
    return str(uuid.uuid4())


@pytest.fixture
def consumer_name():
    return str(uuid.uuid4())


@pytest.fixture
def redis_stream_handler(redis, group_name, consumer_name):
    return GroupStreamHandler(
        group_name=group_name,
        consumer_name=consumer_name,
        client=redis,
        block=None,
        tracker_factory=TrackerFactory(strategy=RedisStreamTrackerStrategy()),
    )
