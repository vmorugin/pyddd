import abc
import datetime as dt
import typing as t
from enum import Enum
from uuid import UUID


class ValueObject: ...


class EntityUid(ValueObject, UUID): ...


MessageTopic: t.TypeAlias = str
IdType = t.TypeVar("IdType")
Version = t.NewType("Version", int)


class IEntity(t.Generic[IdType], abc.ABC):
    @property
    @abc.abstractmethod
    def __reference__(self) -> IdType: ...

    @property
    @abc.abstractmethod
    def __version__(self) -> Version: ...


EntityT = t.TypeVar("EntityT", bound=IEntity)


class MessageType(str, Enum):
    EVENT = "EVENT"
    COMMAND = "COMMAND"


class IMessageMeta(abc.ABCMeta):
    @property
    @abc.abstractmethod
    def __domain__(cls) -> str: ...

    @property
    @abc.abstractmethod
    def __message_name__(cls) -> str: ...

    @property
    @abc.abstractmethod
    def __topic__(cls) -> MessageTopic: ...

    @abc.abstractmethod
    def load(
        cls,
        payload: t.Mapping | str | bytes,
        message_id: UUID | None = None,
        timestamp: dt.datetime | None = None,
    ) -> "IMessage":
        """
        Constructs a new message object.

        Args:
            payload (Union[Mapping, str, bytes]): The payload of the message.
                Any of a dictionary, json string, or bytes.

            message_id (Optional[UUID]): The reference identifier of the message.
                If not provided, a new UUID will be generated.

            timestamp (Optional[datetime]): The creation timestamp of the message.
                If not provided, the current time will be used.

        Returns:
            IMessage: The newly created message object.
        """


class IMessage(abc.ABC, metaclass=IMessageMeta):
    @property
    @abc.abstractmethod
    def __domain__(self) -> str: ...

    @property
    @abc.abstractmethod
    def __message_name__(self) -> str: ...

    @property
    @abc.abstractmethod
    def __topic__(self) -> MessageTopic: ...

    @property
    @abc.abstractmethod
    def __message_id__(self) -> str: ...

    @property
    @abc.abstractmethod
    def __type__(self) -> MessageType: ...

    @property
    @abc.abstractmethod
    def __timestamp__(self) -> dt.datetime: ...

    @abc.abstractmethod
    def to_dict(self) -> dict: ...

    @abc.abstractmethod
    def to_json(self) -> str: ...

    def __repr__(self):
        return f"{self.__topic__}:{self.to_json()}"


class IEvent(IMessage, abc.ABC):
    @property
    def __type__(self) -> MessageType:
        return MessageType.EVENT


EventT = t.TypeVar("EventT", bound=IEvent)


class ISourcedEventMeta(IMessageMeta, abc.ABC): ...


class ISourcedEvent(IEvent, abc.ABC, metaclass=ISourcedEventMeta):
    @abc.abstractmethod
    def mutate(self, entity: t.Optional["IEventSourcedEntity"]) -> t.Optional["IEventSourcedEntity"]: ...

    def apply(self, entity: "IEventSourcedEntity") -> None: ...

    @property
    @abc.abstractmethod
    def __entity_reference__(self): ...

    @property
    @abc.abstractmethod
    def __entity_version__(self) -> Version: ...


class ICommand(IMessage, abc.ABC):
    @property
    def __type__(self) -> MessageType:
        return MessageType.COMMAND


class ICanStoreEvents(t.Generic[EventT], abc.ABC):
    @abc.abstractmethod
    def register_event(self, event: EventT): ...

    @abc.abstractmethod
    def collect_events(self) -> t.Iterable[EventT]: ...


class IRootEntity(IEntity[IdType], ICanStoreEvents[EventT], abc.ABC): ...


class SnapshotABC(abc.ABC):
    @property
    @abc.abstractmethod
    def __state__(self) -> bytes: ...

    @property
    @abc.abstractmethod
    def __reference__(self): ...

    @property
    @abc.abstractmethod
    def __version__(self) -> int: ...


class IEventSourcedEntity(IRootEntity[IdType, EventT], abc.ABC):
    @abc.abstractmethod
    def trigger_event(self, event_type: type[EventT]):
        """
        Apply event and update the entity state.
        """

    def snapshot(self) -> SnapshotABC:
        """
        Create snapshot of specific aggregate.
        Need to implement for event-sourcing.
        """
        raise NotImplementedError("Not implemented")

    @classmethod
    def from_snapshot(cls, snapshot: SnapshotABC) -> "IEventSourcedEntity[IdType, EventT]":
        """
        Load entity from specific snapshot
        """
        raise NotImplementedError("Not implemented")


class IDomainEventSubscriber(t.Generic[EventT], abc.ABC):
    @abc.abstractmethod
    def handle(self, event: EventT): ...

    @abc.abstractmethod
    def subscribed_to_type(self) -> type[EventT]: ...
