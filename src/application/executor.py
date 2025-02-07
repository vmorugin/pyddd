import abc
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
