import tenacity as tc
from pyddd.application.abstractions import (
    AnyCallable,
    IRetryStrategy,
)
from tenacity.stop import stop_base
from tenacity.wait import wait_base


class TenacityAsyncRetry(IRetryStrategy):
    def __init__(
            self,
            retry: tc.retry_base = tc.retry_never,
            stop: stop_base = tc.stop_after_attempt(1),
            wait: wait_base = tc.wait_none(),
    ):
        self._retry = retry
        self._stop = stop
        self._wait = wait

    def __call__(self, func: AnyCallable) -> AnyCallable:
        return tc.AsyncRetrying(retry=self._retry, stop=self._stop, wait=self._wait).wraps(func)


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

    def __call__(self, func: AnyCallable) -> AnyCallable:
        return tc.Retrying(retry=self._retry, stop=self._stop, wait=self._wait).wraps(func)
