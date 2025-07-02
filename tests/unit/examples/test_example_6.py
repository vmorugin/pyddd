import abc
import typing as t
import uuid
from collections import defaultdict

import pytest

from pyddd.application import (
    Module,
    Application,
)
from pyddd.domain import (
    DomainName,
)
from pyddd.domain.abstractions import (
    IdType,
)
from pyddd.domain.event_sourcing import EventSourcedEntity, SourcedDomainEvent
from unit.examples.test_example_5 import BaseCommand

__domain__ = DomainName("balance")


class AccountId(str): ...


class Account(EventSourcedEntity[AccountId]):
    owner_id: str
    balance: int

    @classmethod
    def create(cls, owner_id: str) -> "Account":
        return cls._create(AccountCreated, reference=AccountId(uuid.uuid4()), owner_id=owner_id)

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


class IAccountRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, entity: Account): ...

    @abc.abstractmethod
    def get(self, account_id: AccountId): ...


class CreateAccountCommand(BaseCommand, domain=__domain__):
    owner_id: str


class DepositAccountCommand(BaseCommand, domain=__domain__):
    account_id: str
    amount: int


class WithdrawAccountCommand(BaseCommand, domain=__domain__):
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


class InMemoryAccountRepository(IAccountRepository):
    def __init__(self):
        self._streams: dict[str, list[SourcedDomainEvent]] = defaultdict(list)

    def save(self, entity: Account):
        self._streams[entity.__reference__].extend(entity.collect_events())

    def get(self, account_id: AccountId) -> Account:
        events = self._streams[account_id]
        account: t.Optional[Account] = None
        for event in events:
            account = event.mutate(account)
        return account


def test_account():
    app = Application()
    repository = InMemoryAccountRepository()
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
