import abc
import typing as t

from pyddd.application.abstractions import IApplication
from pyddd.infrastructure.transport.core.abstractions import (
    IPublishedMessage,
    IEventFactory,
)


class IMessageHandler(abc.ABC):
    @abc.abstractmethod
    async def read(self, topic: str, limit: int = None) -> t.Sequence[IPublishedMessage]: ...

    @abc.abstractmethod
    async def bind(self, topic: str): ...


class IAskPolicy(abc.ABC):
    @abc.abstractmethod
    async def process(
        self,
        notification: IPublishedMessage,
        event_factory: IEventFactory,
        application: IApplication,
    ): ...


class ICallback(t.Protocol):
    async def __call__(self, message: IPublishedMessage): ...


class INotificationQueue(abc.ABC):
    @abc.abstractmethod
    async def consume(self, callback: ICallback): ...

    @abc.abstractmethod
    async def bind(self, topic: str): ...

    @abc.abstractmethod
    async def stop_consume(self): ...


class AskProtocol(t.Protocol):
    async def __call__(self) -> None: ...


class RejectProtocol(t.Protocol):
    async def __call__(self, requeue: bool) -> None: ...
