import uuid

import pytest

from pyddd.infrastructure.transport.asyncio.redis.stream_group.consumer import (
    GroupStreamHandler,
    RedisStreamTrackerStrategy,
)

from pyddd.infrastructure.transport.core.tracker_factory import (
    TrackerFactory,
)


@pytest.fixture
async def redis(redis_container):
    client = await redis_container.get_async_client()
    yield client


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
