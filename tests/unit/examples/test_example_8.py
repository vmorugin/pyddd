import typing as t
from pyddd.domain.abstractions import (
    ISourcedEvent,
)
from pyddd.domain.event_sourcing import SourcedEntityT
from pyddd.infrastructure.persistence.abstractions import (
    ISnapshotStore,
)
import abc
import sys
import uuid
from uuid import NAMESPACE_URL

import pytest

from pyddd.application import (
    Module,
    Application,
)
from pyddd.domain import (
    DomainName,
    DomainCommand,
)
from pyddd.domain.abstractions import (
    IdType,
)
from pyddd.domain.event_sourcing import (
    EventSourcedEntity,
    SourcedDomainEvent,
)

__domain__ = DomainName("test.example-with-snapshot")

from pyddd.infrastructure.persistence.abstractions import IEventStore

from pyddd.infrastructure.persistence.event_store import (
    InMemoryStore,
    OptimisticConcurrencyError,
)


class AccountId(str): ...


class Account(EventSourcedEntity[AccountId]):
    owner_id: str
    balance: int

    @classmethod
    def generate_id(cls, owner_id: str) -> AccountId:
        return AccountId(uuid.uuid5(NAMESPACE_URL, f"account/{owner_id}"))

    @classmethod
    def create(cls, owner_id: str) -> "Account":
        return cls._create(AccountCreated, reference=cls.generate_id(owner_id), owner_id=owner_id)

    def deposit(self, amount: int):
        if amount <= 0:
            raise ValueError("Only could deposit positive value")
        self.trigger_event(Deposited, amount=amount)

    def withdraw(self, amount: int):
        if self.balance - amount < 0:
            raise ValueError("Not enough money for withdraw")
        self.trigger_event(Withdrew, amount=amount)


class BaseAccountEvent(SourcedDomainEvent, domain=__domain__): ...


class AccountCreated(BaseAccountEvent):
    owner_id: str

    def mutate(self, entity: t.Optional[EventSourcedEntity[IdType]]) -> Account:
        return Account(
            __reference__=self.__entity_reference__,
            __version__=self.__entity_version__,
            owner_id=self.owner_id,
            balance=0,
        )


class Deposited(BaseAccountEvent):
    amount: int

    def apply(self, entity: Account):
        entity.balance += self.amount


class Withdrew(BaseAccountEvent):
    amount: int

    def apply(self, entity: Account):
        entity.balance -= self.amount


module = Module(__domain__)


class BaseCommand(DomainCommand, domain=__domain__): ...


class CreateAccountCommand(BaseCommand):
    owner_id: str


class DepositAccountCommand(BaseCommand):
    account_id: str
    amount: int


class WithdrawAccountCommand(BaseCommand):
    account_id: str
    amount: int


class IAccountRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, entity: Account): ...

    @abc.abstractmethod
    def find_by(self, entity_id: IdType) -> t.Optional[Account]: ...


class AccountRepository(IAccountRepository):
    def __init__(
        self,
        event_store: IEventStore,
        snapshot_store: ISnapshotStore,
        snapshot_interval: int,
    ):
        self._events = event_store
        self._snapshots = snapshot_store
        self._interval = snapshot_interval

    def find_by(self, entity_id: AccountId) -> t.Optional[Account]:
        entity = self._rehydrate(str(entity_id), entity=None, from_version=0, to_version=sys.maxsize)
        return entity

    def save(self, entity: Account):
        events = list(entity.collect_events())
        self._events.append_to_stream(entity.__reference__, events=events)
        self._capture_snapshot(entity, events=events)

    def _capture_snapshot(self, entity: SourcedEntityT, events: list[ISourcedEvent]):
        for i, event in enumerate(events):
            if event.__entity_version__ % self._interval == 0:
                rehydrated_entity = self._rehydrate(
                    stream_name=str(entity.__reference__),
                    entity=entity,
                    from_version=0,
                    to_version=event.__entity_version__,
                )
                assert rehydrated_entity is not None
                self._snapshots.add_snapshot(str(entity.__reference__), rehydrated_entity.snapshot())

    def _rehydrate(
        self,
        stream_name: str,
        entity: t.Optional[Account],
        from_version: int,
        to_version: int,
    ) -> t.Optional[Account]:
        snapshot = self._snapshots.get_last_snapshot(stream_name)
        if snapshot is not None:
            entity = Account.from_snapshot(snapshot)
            from_version = entity.__version__ + 1
        for event in self._events.get_from_stream(stream_name, from_version=from_version, to_version=to_version):
            entity = t.cast(Account, event.mutate(entity))
        return entity


@module.register
def create_account(cmd: CreateAccountCommand, repository: IAccountRepository):
    account = Account.create(owner_id=cmd.owner_id)
    repository.save(account)
    return account.__reference__


@module.register
def deposit_account(cmd: DepositAccountCommand, repository: IAccountRepository):
    account = repository.find_by(AccountId(cmd.account_id))
    account.deposit(cmd.amount)
    repository.save(account)


@module.register
def withdraw_account(cmd: WithdrawAccountCommand, repository: IAccountRepository):
    account = repository.find_by(AccountId(cmd.account_id))
    account.withdraw(cmd.amount)
    repository.save(account)


def test_account():
    app = Application()
    store = InMemoryStore()
    repository = AccountRepository(event_store=store, snapshot_store=store, snapshot_interval=2)
    app.set_defaults(__domain__, repository=repository)
    app.include(module)
    app.run()
    account_id = app.handle(CreateAccountCommand(owner_id="123"))
    
    with pytest.raises(OptimisticConcurrencyError):
        app.handle(CreateAccountCommand(owner_id="123"))

    account = repository.find_by(account_id)

    assert account.owner_id == "123"
    assert account.balance == 0

    app.handle(DepositAccountCommand(account_id=account_id, amount=200))

    account = repository.find_by(account_id)
    assert account.balance == 200

    with pytest.raises(ValueError):
        app.handle(DepositAccountCommand(account_id=account_id, amount=-1))

    app.handle(WithdrawAccountCommand(account_id=account_id, amount=100))

    account = repository.find_by(account_id)
    assert account.balance == 100

    app.handle(WithdrawAccountCommand(account_id=account_id, amount=100))

    account = repository.find_by(account_id)
    assert account.balance == 0

    with pytest.raises(ValueError):
        app.handle(WithdrawAccountCommand(account_id=account_id, amount=1))

    app.stop()
