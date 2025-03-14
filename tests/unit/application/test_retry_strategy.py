import asyncio

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
        async def example_func():
            nonlocal count
            await asyncio.sleep(0.01)
            count -= 1
            if count > 0:
                raise ValueError()
            return True

        count = 3
        assert await example_func() is True
