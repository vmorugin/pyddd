import abc
from typing import (
    ParamSpec,
    Callable,
    Any,
    Protocol,
    Mapping,
)

from domain import DomainCommand
from domain.event import IEvent
from domain.message import IMessage

P = ParamSpec('P')
ResolvedHandlerT = Callable[..., Any]


class IHandler(abc.ABC):

    @abc.abstractmethod
    def resolve(self, message: IMessage) -> ResolvedHandlerT:
        ...

    @abc.abstractmethod
    def set_defaults(self, defaults: dict):
        ...


class IExecutor(abc.ABC):
    @abc.abstractmethod
    def process_handler(self, handler: ResolvedHandlerT, **kwargs):
        ...

    @abc.abstractmethod
    def process_handlers(self, handlers: list[ResolvedHandlerT], **kwargs):
        ...


class ICondition(abc.ABC):
    @abc.abstractmethod
    def check(self, event: IEvent) -> bool:
        ...


class ICommandHandler(IHandler, abc.ABC):
    @abc.abstractmethod
    def get_command_type(self) -> type[DomainCommand]:
        ...


class IPayloadConverter(Protocol):
    def __call__(self, payload: Mapping) -> Mapping:
        ...
