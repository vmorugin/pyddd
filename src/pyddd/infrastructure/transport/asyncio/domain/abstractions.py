import abc
import dataclasses
import typing as t

from pyddd.application import Application
from pyddd.domain.message import Message


class INotification(abc.ABC):
    @property
    @abc.abstractmethod
    def message_id(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def payload(self) -> dict:
        ...

    @abc.abstractmethod
    async def ack(self) -> None:
        ...

    @abc.abstractmethod
    async def reject(self, requeue: bool) -> None:
        ...


class IMessageHandler(abc.ABC):
    @abc.abstractmethod
    async def read(self, topic: str, limit: int = None) -> list[INotification]:
        ...

    @abc.abstractmethod
    async def bind(self, topic: str):
        ...


class IEventFactory(abc.ABC):
    @abc.abstractmethod
    def build_event(self, message: INotification) -> Message:
        ...


class IAskPolicy(abc.ABC):
    @abc.abstractmethod
    async def process(self, notification: INotification, event_factory: IEventFactory, application: Application):
        ...


class ICallback(t.Protocol):
    async def __call__(self, message: INotification):
        ...


class INotificationQueue(abc.ABC):
    @abc.abstractmethod
    async def consume(self, callback: ICallback):
        ...

    @abc.abstractmethod
    async def bind(self, topic: str):
        ...

    @abc.abstractmethod
    async def stop_consume(self):
        ...


class INotificationTracker(abc.ABC):
    @property
    @abc.abstractmethod
    def last_recent_notification_id(self):
        ...

    def track_messages(self, messages: t.Iterable[INotification]):
        ...


class INotificationTrackerFactory(abc.ABC):
    @abc.abstractmethod
    def create_tracker(self, track_key: str) -> INotificationTracker:
        ...


class IMessageConsumer(abc.ABC):
    @abc.abstractmethod
    def subscribe(self, topic: str):
        ...

    @abc.abstractmethod
    def set_application(self, application: Application):
        ...


class AskProtocol(t.Protocol):
    async def __call__(self) -> None:
        ...


class RejectProtocol(t.Protocol):
    async def __call__(self, requeue: bool) -> None:
        ...


@dataclasses.dataclass(frozen=True)
class NotificationTrackerState:
    track_key: str
    last_recent_notification_id: t.Optional[str]


class INotificationTrackerStrategy(abc.ABC):

    @abc.abstractmethod
    def track_most_recent_message(
            self,
            tracker: NotificationTrackerState,
            *messages: INotification,
    ) -> NotificationTrackerState:
        ...

    @abc.abstractmethod
    def create_tracker(self, track_key: str) -> NotificationTrackerState:
        ...
