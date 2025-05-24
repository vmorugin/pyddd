from typing import (
    Generic,
    Optional,
    cast,
)

from .abstractions import (
    TRepo,
    IRepository,
    IUnitOfWork,
    IUnitOfWorkCtxMgr,
    IUnitOfWorkBuilder,
    IRepositoryBuilder,
    ILocker,
    TLock,
    TLockKey,
    ILockerContextT,
)


class NullLocker(ILockerContextT[TLock], Generic[TLock]):
    _instance: Optional["NullLocker"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __call__(self, __lock_key: TLockKey = None, /) -> ILockerContextT:
        return self

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class UnitOfWork(IUnitOfWork, Generic[TRepo]):
    def __init__(self, repository: TRepo):
        self._repository = repository

    @property
    def repository(self) -> TRepo:
        return self._repository

    def apply(self):
        return self._repository.commit()


class UnitOfWorkCtxMgr(IUnitOfWorkCtxMgr[TRepo, TLock], Generic[TRepo, TLock]):
    def __init__(
        self,
        repository_builder: IRepositoryBuilder[TRepo],
        locker: ILockerContextT[TLock],
    ):
        self._uow: IUnitOfWork[TRepo] | None = None
        self._repository_builder = repository_builder
        self._locker_ctx_manager = locker
        self._lock: TLock | None = None
        self._in_context = False

    def __enter__(self) -> IUnitOfWork[TRepo]:
        if self._in_context:
            raise RuntimeError("already enter to context")
        self._in_context = True
        self._lock = self._locker_ctx_manager.__enter__()
        repository = self._repository_builder.__call__(self)
        if not isinstance(repository, IRepository):
            raise TypeError(
                f"{repository} returned from {self._repository_builder!r} is not instance of d3m.uow.IRepository"
            )
        self._uow = self._get_uow(cast(TRepo, repository))
        return self._uow

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._in_context = False
        self._locker_ctx_manager.__exit__(exc_type, exc_val, exc_tb)

    async def __aenter__(self) -> IUnitOfWork[TRepo]:
        if self._in_context:
            raise RuntimeError("already enter to context")
        self._in_context = True
        self._lock = await self._locker_ctx_manager.__aenter__()
        repository = await self._repository_builder.__call__(self)  # type: ignore[misc]
        if not isinstance(repository, IRepository):
            raise TypeError(
                f"{repository} returned from {self._repository_builder!r} is not instance of d3m.uow.IRepository"
            )
        self._uow = self._get_uow(cast(TRepo, repository))
        return self._uow

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._in_context = False
        await self._locker_ctx_manager.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def lock(self) -> TLock:
        if self._lock is None:
            raise RuntimeError("Could not call lock not entered in context")
        return self._lock

    @staticmethod
    def _get_uow(repository: TRepo) -> IUnitOfWork[TRepo]:
        return UnitOfWork(repository)


class UnitOfWorkBuilder(IUnitOfWorkBuilder, Generic[TRepo]):
    def __init__(
        self,
        repository_builder: IRepositoryBuilder[TRepo],
        locker: ILocker[TLock] | None = None,
    ):
        self._repository_builder = repository_builder
        self._locker = locker or NullLocker()  # type: ignore[var-annotated]

    def __call__(self, __lock_key: TLockKey = None, /) -> IUnitOfWorkCtxMgr[TRepo, TLock]:
        """

        Args:
            __lock_key (`TLockKey`): The lock key used for locking the resources. Defaults to `None`.

        Returns:
            `IUnitOfWorkCtxMgr[TRepo, TLock]`: The context manager object that handles the unit of work.

        """
        return self._get_uow_context_manager(self._locker(__lock_key))

    def _get_uow_context_manager(self, locker: ILockerContextT) -> IUnitOfWorkCtxMgr[TRepo, TLock]:
        return UnitOfWorkCtxMgr(self._repository_builder, locker)
