import abc
import datetime as dt
import typing as t
from contextlib import AbstractAsyncContextManager
from typing import ContextManager

from pyddd.domain.abstractions import IEvent

TLock = t.TypeVar("TLock")
TLockKey: t.TypeAlias = str | None

TRepo = t.TypeVar("TRepo")


class IRepository(abc.ABC):
    @abc.abstractmethod
    def commit(self): ...


class IUnitOfWork(t.Generic[TRepo], abc.ABC):
    @property
    @abc.abstractmethod
    def repository(self) -> TRepo: ...

    @abc.abstractmethod
    def apply(self): ...


class IUnitOfWorkCtxMgr(t.Generic[TRepo, TLock], abc.ABC):
    @abc.abstractmethod
    def __enter__(self) -> IUnitOfWork[TRepo]: ...

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb): ...

    @abc.abstractmethod
    async def __aenter__(self) -> IUnitOfWork[TRepo]: ...

    @abc.abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb): ...

    @property
    @abc.abstractmethod
    def lock(self) -> TLock:
        """
        Returns:
            Lock object returned from locker
        """


class IUnitOfWorkBuilder(abc.ABC, t.Generic[TRepo]):
    @abc.abstractmethod
    def __call__(self, lock_key: str | None = None) -> IUnitOfWorkCtxMgr[TRepo, TLock]: ...


class IRepositoryBuilder(t.Generic[TRepo], abc.ABC):
    @abc.abstractmethod
    def __call__(self, __uow_context_manager: IUnitOfWorkCtxMgr[TRepo, TLock]) -> TRepo | t.Awaitable[TRepo]:  # type: ignore[misc]
        ...


class ILockerContextT(ContextManager[TLock], AbstractAsyncContextManager[TLock], abc.ABC): ...


class ILocker(t.Generic[TLock], abc.ABC):
    @abc.abstractmethod
    def __call__(self, __lock_key: TLockKey = None, /) -> ILockerContextT: ...


class IStoredEvent(abc.ABC):
    @property
    @abc.abstractmethod
    def event_id(self) -> int: ...

    @property
    @abc.abstractmethod
    def body(self) -> str: ...

    @property
    @abc.abstractmethod
    def full_name(self) -> str: ...

    @property
    @abc.abstractmethod
    def occurred_on(self) -> dt.datetime: ...


class IEventStore(abc.ABC):
    @abc.abstractmethod
    def stored_events_between(self, low_stored_event_id: int, high_stored_event_id: int) -> list[IStoredEvent]: ...

    @abc.abstractmethod
    def stored_events_since(self, stored_event_id: int) -> list[IStoredEvent]: ...

    @abc.abstractmethod
    def append(self, event: IEvent) -> IStoredEvent: ...

    @abc.abstractmethod
    def count_stored_events(self) -> int: ...
