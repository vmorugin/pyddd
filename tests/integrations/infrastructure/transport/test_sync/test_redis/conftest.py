import uuid

import pytest
from redis import Redis

from pyddd.infrastructure.transport.sync.redis.stream_group.consumer import (
    GroupStreamHandler,
    RedisStreamTrackerStrategy,
)
from pyddd.infrastructure.transport.core.tracker_factory import (
    TrackerFactory,
)


@pytest.fixture
def redis(redis_container):
    return Redis(host=redis_container["host"], port=redis_container["port"])


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
