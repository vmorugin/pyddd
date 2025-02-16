import abc
from typing import (
    ParamSpec,
    Callable,
    Protocol,
    Mapping,
    TypeVar,
    Sequence,
)

from pyddd.domain import DomainCommand
from pyddd.domain.event import IEvent
from pyddd.domain.message import IMessage

P = ParamSpec('P')
R = TypeVar('R')
AnyCallable = Callable[..., R]


class IHandler(abc.ABC):

    @abc.abstractmethod
    def resolve(self, message: IMessage) -> AnyCallable:
        ...

    @abc.abstractmethod
    def set_defaults(self, defaults: dict):
        ...


class ICommandHandler(IHandler, abc.ABC):
    @abc.abstractmethod
    def get_command_type(self) -> type[DomainCommand]:
        ...


class IExecutor(abc.ABC):
    @abc.abstractmethod
    def process_handler(self, handler: AnyCallable, **kwargs):
        ...

    @abc.abstractmethod
    def process_handlers(self, handlers: list[AnyCallable], **kwargs):
        ...


class ICondition(abc.ABC):
    @abc.abstractmethod
    def check(self, event: IEvent) -> bool:
        ...


class IPayloadConverter(Protocol):
    def __call__(self, payload: Mapping) -> Mapping:
        ...


class IRetryStrategy(abc.ABC):
    @abc.abstractmethod
    def __call__(self, func: AnyCallable) -> AnyCallable:
        ...


class IModule(abc.ABC):
    @property
    @abc.abstractmethod
    def domain(self) -> str:
        ...

    @abc.abstractmethod
    def set_defaults(self, defaults: dict):
        ...

    @abc.abstractmethod
    def register(self, func):
        ...

    @abc.abstractmethod
    def subscribe(
            self,
            event_name: str,
            *,
            converter: IPayloadConverter,
            condition: ICondition,
            retry_strategy: IRetryStrategy,
    ):
        ...

    @abc.abstractmethod
    def get_command_handler(self, command: IMessage) -> AnyCallable:
        ...

    @abc.abstractmethod
    def get_event_handlers(self, event: IMessage) -> Sequence[AnyCallable]:
        ...


class IApplication(abc.ABC):
    @abc.abstractmethod
    def set_defaults(self, domain: str, **kwargs):
        ...

    @abc.abstractmethod
    def include(self, module: IModule):
        ...

    @abc.abstractmethod
    def handle(self, message: IMessage, **depends):
        ...

    @abc.abstractmethod
    def run(self):
        ...
