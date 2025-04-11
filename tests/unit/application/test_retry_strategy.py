import asyncio
from functools import partial

import pytest

from pyddd.application.abstractions import (
    IRetryStrategy,
)
from pyddd.application.retry.none import NoneRetryStrategy


class TestNoneRetryStrategy:
    def test_must_implement_interface(self):
        strategy = NoneRetryStrategy()
        assert isinstance(strategy, IRetryStrategy)

    def test_must_do_nothing(self):
        def mock_func():
            return 1

        strategy = NoneRetryStrategy()
        result = strategy(mock_func)()
        assert result == 1


class TestTenacityRetryExample:
    def test_can_implement_with_sync_tenacity(self):
        pytest.importorskip("tenacity")
        from pyddd.application.retry.tc_retry import TenacitySyncRetry
        import tenacity as tc

        @TenacitySyncRetry(
            retry=tc.retry_if_exception_type(Exception),
            stop=tc.stop_after_attempt(3),
        )
        @partial
        def example_func():
            nonlocal count
            count -= 1
            if count > 0:
                raise ValueError()
            return True

        count = 3
        assert example_func() is True

    async def test_can_implement_with_async_tenacity(self):
        pytest.importorskip("tenacity")
        from pyddd.application.retry.tc_retry import TenacityAsyncRetry
        import tenacity as tc

        @TenacityAsyncRetry(
            retry=tc.retry_if_exception_type(Exception),
            stop=tc.stop_after_attempt(3),
        )
        @partial
        async def example_func():
            nonlocal count
            await asyncio.sleep(0)
            count -= 1
            if count > 0:
                raise ValueError()
            return True

        count = 3
        assert await example_func() is True


class TestBackoffRetry:
    def test_can_implement_with_backoff(self):
        pytest.importorskip("backoff")
        from pyddd.application.retry.backoff import OnException

        count = 3

        @OnException(on_exc=Exception, base=0, factor=0, max_tries=count)
        @partial
        def example_func():
            nonlocal count
            count -= 1
            if count > 0:
                raise ValueError()
            return True

        assert example_func() is True

    async def test_can_implement_with_async_tenacity(self):
        pytest.importorskip("backoff")
        from pyddd.application.retry.backoff import OnException

        count = 3

        @OnException(on_exc=Exception, base=0, factor=0, max_tries=count)
        @partial
        async def example_func():
            nonlocal count
            await asyncio.sleep(0)
            count -= 1
            if count > 0:
                raise ValueError()
            return True

        assert await example_func() is True
