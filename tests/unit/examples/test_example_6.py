import abc
import sys
import typing as t
import uuid

import pytest

from pyddd.application import (
    Module,
    Application,
)
from pyddd.domain import (
    DomainName,
    DomainCommand,
    DomainEvent,
)
from pyddd.domain.abstractions import (
    IEvent,
)
from pyddd.domain.entity import (
    ESRootEntity,
    when,
)
from pyddd.infrastructure.persistence.abstractions import IEventStore

__domain__ = DomainName("balance")

from pyddd.infrastructure.persistence.event_store.in_memory import InMemoryStore


class AccountId(str): ...


class BaseAccountEvent(DomainEvent, domain=__domain__): ...


class AccountCreated(BaseAccountEvent):
    owner_id: str


class Deposited(BaseAccountEvent):
    amount: int


class Withdrew(BaseAccountEvent):
    amount: int


class Account(ESRootEntity[AccountId]):
    owner_id: str = ""
    balance: int = 0

    @classmethod
    def create(cls, owner_id: str) -> "Account":
        self = cls(__reference__=AccountId(uuid.uuid4()))
        self.trigger_event(AccountCreated, owner_id=owner_id)
        return self

    @classmethod
    def from_events(cls, reference: AccountId, events: t.Iterable[IEvent]) -> "Account":
        self = cls(__reference__=reference)
        for event in events:
            self.apply(event)
        return self

    def deposit(self, amount: int):
        if amount <= 0:
            raise ValueError("Only could deposit positive value")
        self.trigger_event(Deposited, amount=amount)

    def withdraw(self, amount: int):
        if self.balance - amount < 0:
            raise ValueError("Not enough money for withdraw")
        self.trigger_event(Withdrew, amount=amount)

    @when
    def created(self, event: AccountCreated):
        self.owner_id = event.owner_id
        self.balance = 0

    @when
    def deposited(self, event: Deposited):
        self.balance += event.amount

    @when
    def withdrew(self, event: Withdrew):
        self.balance -= event.amount


module = Module(__domain__)


class IAccountRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, entity: Account): ...

    @abc.abstractmethod
    def get(self, account_id: AccountId): ...


class BaseCommand(DomainCommand, domain=__domain__): ...


class CreateAccountCommand(BaseCommand):
    owner_id: str


class DepositAccountCommand(BaseCommand):
    account_id: str
    amount: int


class WithdrawAccountCommand(BaseCommand):
    account_id: str
    amount: int


@module.register
def create_account(cmd: CreateAccountCommand, repository: IAccountRepository):
    account = Account.create(owner_id=cmd.owner_id)
    repository.save(account)
    return account.__reference__


@module.register
def deposit_account(cmd: DepositAccountCommand, repository: IAccountRepository):
    account = repository.get(AccountId(cmd.account_id))
    account.deposit(cmd.amount)
    repository.save(account)


@module.register
def withdraw_account(cmd: WithdrawAccountCommand, repository: IAccountRepository):
    account = repository.get(AccountId(cmd.account_id))
    account.withdraw(cmd.amount)
    repository.save(account)


class AccountRepository(IAccountRepository):
    def __init__(self, store: IEventStore):
        self._store = store

    def save(self, entity: Account):
        self._store.append_to_stream(str(entity.__reference__), entity.collect_events())

    def get(self, account_id: AccountId) -> Account:
        stream = self._store.get_stream(str(account_id), 0, sys.maxsize)
        account = Account.from_events(account_id, stream)
        return account


def test_account():
    app = Application()
    event_store = InMemoryStore()
    repository = AccountRepository(event_store)
    app.set_defaults(__domain__, repository=repository)
    app.include(module)
    app.run()

    account_id = app.handle(CreateAccountCommand(owner_id="123"))

    account = repository.get(account_id)

    assert account.owner_id == "123"
    assert account.balance == 0

    app.handle(DepositAccountCommand(account_id=account_id, amount=200))

    account = repository.get(account_id)
    assert account.balance == 200

    with pytest.raises(ValueError):
        app.handle(DepositAccountCommand(account_id=account_id, amount=-1))

    app.handle(WithdrawAccountCommand(account_id=account_id, amount=100))

    account = repository.get(account_id)
    assert account.balance == 100

    app.handle(WithdrawAccountCommand(account_id=account_id, amount=100))

    account = repository.get(account_id)
    assert account.balance == 0

    with pytest.raises(ValueError):
        app.handle(WithdrawAccountCommand(account_id=account_id, amount=1))

    app.stop()
