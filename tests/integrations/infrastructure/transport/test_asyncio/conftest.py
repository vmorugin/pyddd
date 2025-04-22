import os
import uuid

import pytest
from redis.asyncio import Redis

from pyddd.infrastructure.transport.asyncio.redis.stream_group.consumer import (
    GroupStreamHandler,
    RedisStreamTrackerStrategy,
)
from pyddd.infrastructure.transport.core.tracker_factory import NotificationTrackerFactory


@pytest.fixture
def redis():
    return Redis(host=os.getenv('REDIS_HOST'))


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
        tracker_factory=NotificationTrackerFactory(strategy=RedisStreamTrackerStrategy())
    )
