from pyddd.application import IRetryStrategy
from pyddd.application.abstractions import AnyCallable
from backoff import (
    on_exception,
    expo,
)


class OnException(IRetryStrategy):
    def __init__(
        self,
        on_exc: type[Exception],
        base: float = 1.05,
        factor: float = 1,
        max_tries: int = 5,
    ):
        self._on_exc = on_exc
        self._base = base
        self._max_tries = max_tries
        self._factor = factor

    def __call__(self, func: AnyCallable):
        wrapper = on_exception(
            expo,
            self._on_exc,
            base=self._base,
            max_tries=self._max_tries,
            factor=self._factor,
        )
        func.__name__ = wrapper.__name__
        return wrapper(func)
