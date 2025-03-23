import abc
import typing as t

from pyddd.application.abstractions import IApplication
from pyddd.domain.message import (
    Message,
    IMessage,
)
from pyddd.infrastructure.transport.core.value_objects import NotificationTrackerState


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
    def ack(self):
        ...

    @abc.abstractmethod
    def reject(self, requeue: bool):
        ...


class IEventFactory(abc.ABC):
    @abc.abstractmethod
    def build_event(self, message: INotification) -> Message:
        ...


class INotificationTracker(abc.ABC):
    @property
    @abc.abstractmethod
    def last_recent_notification_id(self):
        ...

    @abc.abstractmethod
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
    def set_application(self, application: IApplication):
        ...


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


class PublisherProtocol(t.Protocol):
    def __call__(self, message: IMessage):
        ...
