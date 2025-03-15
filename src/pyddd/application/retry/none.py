from pyddd.application.abstractions import (
    IRetryStrategy,
    AnyCallable,
)


class NoneRetryStrategy(IRetryStrategy):
    def __call__(self, func: AnyCallable) -> AnyCallable:
        return func


none_retry = NoneRetryStrategy()
