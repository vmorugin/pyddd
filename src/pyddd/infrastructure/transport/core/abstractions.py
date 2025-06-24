import abc
import typing as t

from pyddd.application.abstractions import IApplication
from pyddd.domain.abstractions import IMessage
from pyddd.infrastructure.transport.core.value_objects import TrackerState


class IPublishingMessage(abc.ABC):
    @property
    @abc.abstractmethod
    def message_id(self) -> str: ...

    @property
    @abc.abstractmethod
    def name(self) -> str: ...

    @property
    @abc.abstractmethod
    def payload(self) -> dict: ...


class IPublishedMessage(IPublishingMessage, abc.ABC):
    @abc.abstractmethod
    def ack(self): ...

    @abc.abstractmethod
    def reject(self, requeue: bool): ...


class IEventFactory(abc.ABC):
    @abc.abstractmethod
    def build_event(self, notification: IPublishingMessage) -> IMessage: ...

    @abc.abstractmethod
    def build_publishing_message(self, message: IMessage) -> IPublishingMessage: ...


class ITracker(abc.ABC):
    @property
    @abc.abstractmethod
    def last_recent_message_id(self): ...

    @abc.abstractmethod
    def track_messages(self, messages: t.Iterable[IPublishedMessage]): ...


class ITrackerFactory(abc.ABC):
    @abc.abstractmethod
    def create_tracker(self, track_key: str) -> ITracker: ...


class IMessageConsumer(abc.ABC):
    @abc.abstractmethod
    def subscribe(self, topic: str): ...

    @abc.abstractmethod
    def set_application(self, application: IApplication): ...


class ITrackerStrategy(abc.ABC):
    @abc.abstractmethod
    def track_most_recent_message(
        self,
        tracker: TrackerState,
        *messages: IPublishedMessage,
    ) -> TrackerState: ...

    @abc.abstractmethod
    def create_tracker(self, track_key: str) -> TrackerState: ...


class PublisherProtocol(t.Protocol):
    def __call__(self, message: IMessage): ...
