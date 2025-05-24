from __future__ import annotations
import abc
import typing as t
from enum import Enum

from pyddd.domain.command import DomainCommand
from pyddd.domain.abstractions import IMessage

R = t.TypeVar("R")
AnyCallable = t.Callable[..., R]


class IHandler(abc.ABC):
    @abc.abstractmethod
    def resolve(self, message: IMessage) -> AnyCallable: ...

    @abc.abstractmethod
    def set_defaults(self, defaults: dict): ...


class ICommandHandler(IHandler, abc.ABC):
    @abc.abstractmethod
    def get_command_type(self) -> type[DomainCommand]: ...


class IExecutor(abc.ABC):
    @abc.abstractmethod
    def process_handler(self, handler: AnyCallable, **kwargs): ...

    @abc.abstractmethod
    def process_handlers(self, handlers: list[AnyCallable], **kwargs): ...


class ICondition(abc.ABC):
    @abc.abstractmethod
    def check(self, event: IMessage) -> bool: ...


class IPayloadConverter(t.Protocol):
    def __call__(self, payload: t.Mapping) -> t.Mapping: ...


class IRetryStrategy(abc.ABC):
    @abc.abstractmethod
    def __call__(self, func: AnyCallable) -> AnyCallable: ...


class ISubscribe(abc.ABC):
    @abc.abstractmethod
    def subscribe(
        self,
        event_name: str,
        *,
        converter: IPayloadConverter,
        condition: ICondition,
        retry_strategy: IRetryStrategy,
    ): ...


class IRegister(abc.ABC):
    @abc.abstractmethod
    def register(self, func): ...


class IModule(abc.ABC):
    @property
    @abc.abstractmethod
    def domain(self) -> str: ...

    @abc.abstractmethod
    def set_defaults(self, defaults: dict): ...

    @abc.abstractmethod
    def get_command_handler(self, command: IMessage) -> AnyCallable: ...

    @abc.abstractmethod
    def get_event_handlers(self, event: IMessage) -> t.Sequence[AnyCallable]: ...


class IApplication(abc.ABC):
    @abc.abstractmethod
    def set_defaults(self, domain: str, **kwargs): ...

    @abc.abstractmethod
    def include(self, module: IModule): ...

    @abc.abstractmethod
    def handle(self, message: IMessage, **depends): ...

    @abc.abstractmethod
    def run(self): ...

    @abc.abstractmethod
    async def run_async(self): ...

    @abc.abstractmethod
    def stop(self): ...

    @abc.abstractmethod
    async def stop_async(self): ...

    @abc.abstractmethod
    def subscribe(self, signal: ApplicationSignal, listener: SignalListener): ...

    @abc.abstractmethod
    def unsubscribe(self, signal: ApplicationSignal, listener: SignalListener): ...


_AppT = t.TypeVar("_AppT", bound=IApplication)

Lifespan = t.Callable[[_AppT], t.ContextManager[None] | t.AsyncContextManager[None]]


class ApplicationSignal(str, Enum):
    BEFORE_RUN = "before_run"
    AFTER_RUN = "after_run"
    BEFORE_STOP = "before_stop"
    AFTER_STOP = "after_stop"


SignalListener = t.Callable[[ApplicationSignal, IApplication], t.Any]


class ISignalManager(abc.ABC):
    @abc.abstractmethod
    def subscribe(self, signal: ApplicationSignal, listener: SignalListener): ...

    @abc.abstractmethod
    def unsubscribe(self, signal: ApplicationSignal, listener: SignalListener): ...

    @abc.abstractmethod
    def notify(self, signal: ApplicationSignal, application: IApplication): ...

    @abc.abstractmethod
    async def notify_async(self, signal: ApplicationSignal, application: IApplication): ...
