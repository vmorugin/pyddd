import abc
import logging

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
from concurrent.futures import ThreadPoolExecutor


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
        result = []
        for handler in handlers:
            try:
                result.append(handler.handle(event, **kwargs))
            except Exception as exc:
                self._logger.warning(f'Unhandled event {event}', exc_info=exc)
                result.append(exc)
        return result

class ThreadExecutor(IExecutor):
    def __init__(self, logger_name: str = 'pyddd.executor'):
        self._logger = logging.getLogger(logger_name)

    def process_command(self, command: DomainCommand, handler: CommandHandler, **kwargs):
        return handler.handle(command, **kwargs)

    def process_event(self, event: DomainEvent, handlers: list[EventHandler], **kwargs):
        result = []
        futures = []
        with ThreadPoolExecutor() as pool:
            for handler in handlers:
                future = pool.submit(handler.handle, event, **kwargs)
                futures.append(future)
        while futures:
            future = futures.pop(0)
            if future.running():
                futures.insert(0, future)
            elif exc := future.exception():
                self._logger.warning(f'Unhandled event {event}', exc_info=exc)
                result.append(exc)
            else:
                result.append(future.result())
        return result

