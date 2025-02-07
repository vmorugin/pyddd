import abc
import asyncio
import logging
from functools import partial

from application.handler import (
    IHandler,
    CommandHandler,
    EventHandler,
)
from domain.message import (
    IMessage,
)
from domain import (
    DomainCommand,
    DomainEvent,
)
from concurrent.futures import (
    ThreadPoolExecutor,
)


class IExecutor(abc.ABC):
    @abc.abstractmethod
    def process_command(self, command: IMessage, handler: IHandler, **kwargs):
        ...

    @abc.abstractmethod
    def process_event(self, event: IMessage, handlers: list[IHandler], **kwargs):
        ...


class SyncExecutor(IExecutor):
    def __init__(self, logger_name: str = 'pyddd.executor'):
        self._logger = logging.getLogger(logger_name)

    def process_command(self, command: DomainCommand, handler: CommandHandler, **kwargs):
        return handler.handle(command, **kwargs)

    def process_event(self, event: DomainEvent, handlers: list[EventHandler], **kwargs):
        with ThreadPoolExecutor() as pool:
            func = partial(self._process_handler, event=event, **kwargs)
            return list(pool.map(func, handlers))

    def _process_handler(self, handler: EventHandler, event: DomainEvent, **kwargs):
        try:
            return handler.handle(event, **kwargs)
        except Exception as exc:
            self._logger.warning(f'Unhandled event {event}', exc_info=exc)
            return exc


class AsyncExecutor(IExecutor):

    def process_command(self, command: IMessage, handler: IHandler, **kwargs):
        future = asyncio.Future()
        task = asyncio.create_task(handler.handle(message=command, **kwargs))
        task.add_done_callback(partial(self._set_task_result, future=future))
        return future

    def process_event(self, event: IMessage, handlers: list[IHandler], **kwargs):
        future = asyncio.Future()
        tasks = []
        for handler in handlers:
            tasks.append(asyncio.create_task(handler.handle(event, **kwargs)))
        result = asyncio.gather(*tasks, return_exceptions=True)
        result.add_done_callback(partial(self._set_task_result, future=future))
        return future

    @staticmethod
    def _set_task_result(task: asyncio.Future, /, future: asyncio.Future):
        if task.exception() is not None:
            future.set_exception(task.exception())  # type: ignore
        else:
            future.set_result(task.result())
