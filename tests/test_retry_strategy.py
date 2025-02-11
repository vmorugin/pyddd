import pytest

from pyddd.application.retry import (
    IRetryStrategy,
    ResolvedHandlerT,
    NoneRetryStrategy
)


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
    def test_can_implement_with_tenacity(self):
        pytest.importorskip("tenacity")

        import tenacity as tc
        from tenacity.stop import stop_base
        from tenacity.wait import wait_base

        class TenacitySyncRetry(IRetryStrategy):
            def __init__(
                    self,
                    retry: tc.retry_base = tc.retry_never,
                    stop: stop_base = tc.stop_after_attempt(1),
                    wait: wait_base = tc.wait_none(),
            ):
                self._retry = retry
                self._stop = stop
                self._wait = wait

            def __call__(self, func: ResolvedHandlerT) -> ResolvedHandlerT:
                return tc.Retrying(retry=self._retry, stop=self._stop, wait=self._wait).wraps(func)

        tc_retry = TenacitySyncRetry

        @tc_retry(
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
