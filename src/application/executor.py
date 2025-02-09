import asyncio
import logging
from functools import partial

from application.abstractions import (
    IExecutor,
    ResolvedHandlerT,
)
from concurrent.futures import (
    ThreadPoolExecutor,
)


class SyncExecutor(IExecutor):
    def __init__(self, logger_name: str = 'pyddd.executor'):
        self._logger = logging.getLogger(logger_name)

    def process_handler(self, handler: ResolvedHandlerT, **kwargs):
        return handler(**kwargs)

    def process_handlers(self, handlers: list[ResolvedHandlerT], **kwargs):
        with ThreadPoolExecutor() as pool:
            func = partial(self._process_handler, **kwargs)
            return list(pool.map(func, handlers))

    def _process_handler(self, handler: ResolvedHandlerT, **kwargs):
        try:
            return handler(**kwargs)
        except Exception as exc:
            self._logger.warning(f'Failed to process handler {handler}', exc_info=exc)
            return exc


class AsyncExecutor(IExecutor):

    def process_handler(self, handler: ResolvedHandlerT, **kwargs):
        future = asyncio.Future()
        task = asyncio.create_task(handler(**kwargs))
        task.add_done_callback(partial(self._set_task_result, future=future))
        return future

    def process_handlers(self, handlers: list[ResolvedHandlerT], **kwargs):
        future = asyncio.Future()
        tasks = []
        for handler in handlers:
            tasks.append(asyncio.create_task(handler(**kwargs)))
        result = asyncio.gather(*tasks, return_exceptions=True)
        result.add_done_callback(partial(self._set_task_result, future=future))
        return future

    @staticmethod
    def _set_task_result(task: asyncio.Future, /, future: asyncio.Future):
        if task.exception() is not None:
            future.set_exception(task.exception())  # type: ignore
        else:
            future.set_result(task.result())
