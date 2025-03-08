import abc
from pyddd.domain.message import (
    IMessage,
    MessageType,
    BaseDomainMessage,
    BaseDomainMessageMeta,
)


class _DomainCommandMeta(BaseDomainMessageMeta):
    def __init__(cls, name, bases, namespace, *, domain: str = None):
        super().__init__(name, bases, namespace, domain=domain)
        if domain is None and cls.__module__ != __name__:
            try:
                _ = cls._domain_name
            except AttributeError:
                raise ValueError(
                    f"required set domain name for command '{cls.__module__}.{cls.__name__}'"
                )


class ICommand(IMessage, abc.ABC):
    @property
    def __type__(self) -> MessageType:
        return MessageType.COMMAND


class DomainCommand(BaseDomainMessage, ICommand, metaclass=_DomainCommandMeta):
    ...
