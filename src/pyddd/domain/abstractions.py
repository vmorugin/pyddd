import abc
import datetime as dt
import typing as t
from enum import Enum
from uuid import UUID


class ValueObject: ...


class EntityUid(ValueObject, UUID): ...


IdType = t.TypeVar("IdType")


class IEntity(t.Generic[IdType], abc.ABC):
    @property
    @abc.abstractmethod
    def __reference__(self) -> IdType: ...


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
    def __topic__(cls) -> str: ...

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
    def __topic__(self) -> str: ...

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


class ICommand(IMessage, abc.ABC):
    @property
    def __type__(self) -> MessageType:
        return MessageType.COMMAND


class IRootEntity(IEntity[IdType], abc.ABC):
    @abc.abstractmethod
    def register_event(self, event: IEvent): ...

    @abc.abstractmethod
    def collect_events(self) -> list[IEvent]: ...
