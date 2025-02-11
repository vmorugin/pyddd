from pyddd.application.abstractions import (
    IRetryStrategy,
    ResolvedHandlerT,
)


class NoneRetryStrategy(IRetryStrategy):
    def __call__(self, func: ResolvedHandlerT) -> ResolvedHandlerT:
        return func

none_retry = NoneRetryStrategy()