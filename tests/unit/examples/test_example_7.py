import typing as t
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

__domain__ = DomainName("balance.example")

from pyddd.infrastructure.persistence.abstractions import IESRepository
from pyddd.infrastructure.persistence.event_store import (
    InMemoryStore,
    OptimisticConcurrencyError,
)

from pyddd.infrastructure.persistence.event_store.repository import (
    EventSourcedRepository,
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


@module.register
def create_account(cmd: CreateAccountCommand, repository: IESRepository[Account]):
    account = Account.create(owner_id=cmd.owner_id)
    repository.add(account)
    repository.commit()
    return account.__reference__


@module.register
def deposit_account(cmd: DepositAccountCommand, repository: IESRepository[Account]):
    account = repository.find_by(AccountId(cmd.account_id))
    account.deposit(cmd.amount)
    repository.commit()


@module.register
def withdraw_account(cmd: WithdrawAccountCommand, repository: IESRepository[Account]):
    account = repository.find_by(AccountId(cmd.account_id))
    account.withdraw(cmd.amount)
    repository.commit()


def test_account():
    app = Application()
    store = InMemoryStore()
    repository = EventSourcedRepository(event_store=store)
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
