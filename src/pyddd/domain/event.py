from pyddd.domain.message import (
    BaseDomainMessage,
    BaseDomainMessageMeta,
)
from pyddd.domain.abstractions import (
    IEvent,
)


class _DomainEventMeta(BaseDomainMessageMeta):
    def __init__(cls, name, bases, namespace, *, domain: str = None):
        super().__init__(name, bases, namespace, domain=domain)
        if domain is None and cls.__module__ != __name__:
            try:
                _ = cls.__domain__
            except AttributeError:
                raise ValueError(f"required set domain name for '{cls.__module__}.{cls.__name__}'")


class DomainEvent(BaseDomainMessage, IEvent, metaclass=_DomainEventMeta): ...
