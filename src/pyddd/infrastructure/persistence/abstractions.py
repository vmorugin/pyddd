import abc
import typing as t
from contextlib import AbstractAsyncContextManager
from typing import ContextManager

from pyddd.domain.abstractions import (
    ISourcedEvent,
)
from pyddd.domain.event_sourcing import SnapshotABC

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


class IEventStore(abc.ABC):
    @abc.abstractmethod
    def append_to_stream(
        self, stream_name: str, events: t.Iterable[ISourcedEvent], expected_version: t.Optional[int] = None
    ):
        """
        Add events to existed stream.
        Expected version - optimistic lock checker, implemented by repository.
        """

    @abc.abstractmethod
    def get_from_stream(
        self,
        stream_name: str,
        from_version: int,
        to_version: int,
    ) -> t.Union[t.Iterable[ISourcedEvent], t.Awaitable[t.Iterable[ISourcedEvent]]]:
        """
        Get Events from stream sorted by version, from and to included.
        Raise events if not created.
        """

    @abc.abstractmethod
    def add_snapshot(self, stream_name: str, snapshot: SnapshotABC):
        """
        Add snapshot to stream.
        """

    @abc.abstractmethod
    def get_last_snapshot(
        self,
        stream_name: str,
    ) -> t.Union[t.Optional[SnapshotABC], t.Awaitable[t.Optional[SnapshotABC]]]:
        """
        Find latest snapshot from stream.
        """
