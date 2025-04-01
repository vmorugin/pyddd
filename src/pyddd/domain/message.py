import abc
import datetime as dt
import json
from enum import Enum
from typing import (
    Optional,
    Union,
)
from uuid import (
    uuid4,
    UUID,
)
from importlib.metadata import version

pydantic_version = version('pydantic')

if pydantic_version.startswith('2'):
    from pydantic import BaseModel, PrivateAttr
    from pydantic._internal._model_construction import ModelMetaclass
elif pydantic_version.startswith('1'):
    from pydantic.main import ModelMetaclass, BaseModel, PrivateAttr  # type: ignore[no-redef]
else:
    raise ImportError('Can not import pydantic. Please setup pydantic >= 1.x.x <= 2.x.x')


class MessageType(str, Enum):
    EVENT = 'EVENT'
    COMMAND = 'COMMAND'


class IMessageMeta(abc.ABCMeta):

    @property
    @abc.abstractmethod
    def __domain__(cls) -> str:
        ...

    @property
    @abc.abstractmethod
    def __message_name__(cls) -> str:
        ...

    @property
    @abc.abstractmethod
    def __topic__(cls) -> str:
        ...


class IMessage(abc.ABC, metaclass=IMessageMeta):

    @property
    @abc.abstractmethod
    def __domain__(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def __message_name__(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def __topic__(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def __message_id__(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def __type__(self) -> MessageType:
        ...

    @property
    @abc.abstractmethod
    def __timestamp__(self) -> dt.datetime:
        ...

    @abc.abstractmethod
    def to_dict(self) -> dict:
        ...

    @abc.abstractmethod
    def to_json(self) -> str:
        ...


class Message(IMessage):
    def __init__(
            self,
            full_name: str,
            message_type: Union[MessageType, str],
            payload: dict,
            message_id: Optional[str] = None,
            occurred_on: Optional[dt.datetime] = None,
    ):
        self._domain, self._name = full_name.rsplit('.', 1)
        self._type = MessageType(message_type)
        self._payload = json.dumps(payload)
        self._message_id = message_id or str(uuid4())
        self._occurred_on = occurred_on or dt.datetime.utcnow()

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
    def __topic__(self) -> str:
        return f'{self._domain}.{self._name}'

    def to_dict(self) -> dict:
        return json.loads(self._payload)

    def to_json(self) -> str:
        return self._payload


class BaseDomainMessageMeta(IMessageMeta, ModelMetaclass, abc.ABCMeta):
    _domain_name: str
    _message_name: str

    def __new__(mcs, name, bases, namespace, domain: Optional[str] = None):
        cls = super().__new__(mcs, name, bases, namespace)
        if domain is not None:
            cls._domain_name = domain  # type: ignore[attr-defined]
        return cls

    def __init__(cls, name, bases, namespace, *, domain: Optional[str] = None):
        super().__init__(name, bases, namespace, domain=domain)
        cls._message_name = name

    @property
    def __domain__(cls) -> str:
        return cls._get_domain_name()

    @property
    def __message_name__(cls) -> str:
        return cls._get_message_name()

    @property
    def __topic__(cls) -> str:
        return cls._get_topic()

    def _get_topic(cls):
        return f"{cls._domain_name}.{cls._message_name}"

    def _get_message_name(cls):
        return cls._message_name

    def _get_domain_name(cls):
        return cls._domain_name


class BaseDomainMessage(BaseModel, IMessage, abc.ABC, metaclass=BaseDomainMessageMeta):
    _occurred_on: dt.datetime = PrivateAttr(default_factory=lambda: dt.datetime.utcnow())
    _reference: UUID = PrivateAttr(default_factory=uuid4)

    class Config:
        frozen = True

    @classmethod  # type: ignore[misc]
    @property
    def __domain__(cls) -> str:
        return cls._get_domain_name()

    @classmethod  # type: ignore[misc]
    @property
    def __message_name__(cls) -> str:
        return cls._get_message_name()

    @classmethod  # type: ignore[misc]
    @property
    def __topic__(cls) -> str:
        return cls._get_topic()

    @property
    def __message_id__(self) -> str:
        return str(self._reference)

    @property
    def __timestamp__(self) -> dt.datetime:
        return self._occurred_on

    def to_dict(self) -> dict:
        return self.dict()

    def to_json(self) -> str:
        return self.json()
