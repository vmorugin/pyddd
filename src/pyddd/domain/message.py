import abc
import datetime as dt
import json
from contextlib import suppress
from typing import (
    Optional,
    Union,
    Mapping,
    TypeVar,
)
from uuid import (
    uuid4,
    UUID,
)
from importlib.metadata import version as package_version

from pyddd.domain.types import DomainName
from pyddd.domain.abstractions import (
    MessageType,
    IMessageMeta,
    IMessage,
    Version,
    MessageTopic,
)

from pydantic import (
    BaseModel,
    PrivateAttr,
    root_validator,
)

pydantic_version = package_version("pydantic")

if pydantic_version.startswith("2"):
    from pydantic._internal._model_construction import ModelMetaclass
elif pydantic_version.startswith("1"):
    from pydantic.main import ModelMetaclass  # type: ignore[no-redef]
else:
    raise ImportError("Can not import pydantic. Please setup pydantic >= 1.x.x <= 2.x.x")

_T = TypeVar("_T", bound="BaseDomainMessage")


class _DomainMessagesCollection:
    def __init__(self):
        self._collection: dict[MessageTopic, IMessageMeta] = dict()

    def register(self, topic: MessageTopic, message_cls: IMessageMeta):
        if topic in self._collection and self._collection[topic] != message_cls:
            raise ValueError(f"Message {topic} already registered by another class.")
        self._collection[topic] = message_cls

    def get_class(self, topic: MessageTopic) -> IMessageMeta:
        if topic not in self._collection:
            raise ValueError(f"Could not find message {topic}")
        return self._collection[topic]


_domain_message_collection = _DomainMessagesCollection()


class Message(IMessage):
    def __init__(
        self,
        full_name: str,
        message_type: Union[MessageType, str],
        payload: dict,
        message_id: Optional[str] = None,
        occurred_on: Optional[dt.datetime] = None,
        event_version: Version = Version(1),
    ):
        self._domain, self._name = full_name.rsplit(".", 1)
        self._type = MessageType(message_type)
        self._payload = json.dumps(payload)
        self._message_id = message_id or str(uuid4())
        self._occurred_on = occurred_on or dt.datetime.utcnow()
        self._version = event_version

    @property
    def __message_id__(self) -> str:
        return self._message_id

    @property
    def __type__(self) -> MessageType:
        return self._type

    @property
    def __timestamp__(self) -> dt.datetime:
        return self._occurred_on

    @property
    def __domain__(self) -> str:
        return self._domain

    @property
    def __message_name__(self) -> str:
        return self._name

    @property
    def __version__(self) -> Version:
        return self._version

    @property
    def __topic__(self) -> MessageTopic:
        return MessageTopic(f"{self._domain}.{self._name}")

    def to_dict(self) -> dict:
        return json.loads(self._payload)

    def to_json(self) -> str:
        return self._payload


class BaseDomainMessageMeta(IMessageMeta, ModelMetaclass, abc.ABCMeta):
    _domain_name: DomainName
    _message_name: str
    _version: Version

    def __new__(mcs, name, bases, namespace, domain: Optional[str] = None, version: int = 1):
        cls: "BaseDomainMessageMeta" = super().__new__(mcs, name, bases, namespace)  # type: ignore[assignment]
        if domain is not None:
            cls._domain_name = DomainName(domain)
        return cls

    def __init__(cls, name, bases, namespace, *, domain: Optional[str] = None, version: int = 1):
        super().__init__(name, bases, namespace, domain=domain)
        cls._message_name = name
        cls._version = Version(version)
        with suppress(AttributeError):
            _domain_message_collection.register(cls.__topic__, cls)

    @property
    def __domain__(cls) -> str:
        return cls._domain_name

    @property
    def __message_name__(cls) -> str:
        return cls._message_name

    @property
    def __topic__(cls) -> MessageTopic:
        return MessageTopic(f"{cls._domain_name}.{cls._message_name}")

    @property
    def __version__(cls) -> Version:
        return cls._version

    def load(  # type: ignore[misc]
        cls: type[_T],
        payload: Mapping | str | bytes,
        message_id: UUID | None = None,
        timestamp: dt.datetime | None = None,
        **kwargs,
    ) -> _T:
        obj = cls.parse_obj(payload)
        obj._reference = message_id or UUID(str(obj.__message_id__))
        obj._occurred_on = timestamp or obj.__timestamp__
        return obj


class BaseDomainMessage(BaseModel, IMessage, abc.ABC, metaclass=BaseDomainMessageMeta):
    _occurred_on: dt.datetime = PrivateAttr(default_factory=lambda: dt.datetime.utcnow())
    _reference: UUID = PrivateAttr(default_factory=uuid4)
    _version: Version = PrivateAttr(default=Version(1))

    class Config:
        frozen = True

    @property
    def __domain__(self) -> str:
        return str(self.__class__.__domain__)

    @property
    def __message_name__(self) -> str:
        return str(self.__class__.__message_name__)

    @property
    def __topic__(self) -> MessageTopic:
        cls: BaseDomainMessageMeta = self.__class__
        return cls.__topic__

    @property
    def __message_id__(self) -> str:
        return str(self._reference)

    @property
    def __timestamp__(self) -> dt.datetime:
        return self._occurred_on

    @property
    def __version__(self) -> Version:
        return self._version

    def to_dict(self) -> dict:
        return self.dict()

    def to_json(self) -> str:
        return self.json()

    @root_validator(pre=True, allow_reuse=True)
    def upcast(cls, values):
        class_version = values.get("class_version", 1)
        while class_version != cls._version:
            next_version = class_version + 1
            upcast = getattr(cls, f"upcast_v{class_version}_v{next_version}", None)
            if upcast is None:
                raise ValueError(
                    f"Could not upcast message {cls.__domain__}.{cls.__message_name__} "
                    f"from version {class_version} to {next_version}"
                )
            upcast(values)
            class_version = next_version
        return values


def get_message_class(topic: MessageTopic) -> IMessageMeta:
    return _domain_message_collection.get_class(topic)


def register_message_alias(alias: MessageTopic, message_cls: IMessageMeta):
    _domain_message_collection.register(alias, message_cls)
