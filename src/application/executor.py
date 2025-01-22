import abc

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


class IExecutor(abc.ABC):
    @abc.abstractmethod
    def process_command(self, command: IMessage, handler: IHandler, **kwargs):
        ...

    @abc.abstractmethod
    def process_event(self, event: IMessage, handlers: list[IHandler], **kwargs):
        ...


class SyncExecutor(IExecutor):
    def process_command(self, command: DomainCommand, handler: CommandHandler, **kwargs):
        return handler.handle(command, **kwargs)

    def process_event(self, event: DomainEvent, handlers: list[EventHandler], **kwargs):
        for handler in handlers:
            try:
                handler.handle(event, **kwargs)
            except Exception as ex:
                """Log exception!"""
                pass
