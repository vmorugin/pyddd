import abc
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import singledispatchmethod
from typing import List, Optional
from decimal import Decimal
import typing as t

from pyddd.domain import (
    DomainEvent,
    DomainCommand,
)
from pyddd.domain.abstractions import (
    ValueObject,
    IEvent,
    IdType,
)
from pyddd.domain.entity import (
    Entity,
    ESRootEntity,
)


# Example from V.Vernon's book "Implementing Domain-Driven Design" implemented in Python


class IPricingService(abc.ABC):
    @abc.abstractmethod
    def get_welcome_bonus(self, currency: "Currency") -> "CurrencyAmount": ...

    @abc.abstractmethod
    def get_overdraft_threshold(self, currency: "Currency") -> "CurrencyAmount": ...


# Domain types
class CustomerId(str, ValueObject):
    """Customer identity value object"""


class Currency(str, Enum):
    NONE = "none"
    EUR = "eur"
    USD = "usd"
    RUR = "rur"


@dataclass(frozen=True)
class CurrencyAmount(ValueObject):
    """Currency amount value object with operator overloading"""

    amount: Decimal
    currency: Currency

    def __post_init__(self):
        # Ensure amount is Decimal for precision
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))

    def _check_currency(self, other_currency: Currency, operation: str) -> None:
        if self.currency != other_currency:
            raise ValueError(
                f"Can't perform operation on different currencies: "
                f"{self.currency.value} {operation} {other_currency.value}"
            )

    def __eq__(self, other: "CurrencyAmount") -> bool:
        if not isinstance(other, CurrencyAmount):
            return False
        self._check_currency(other.currency, "==")
        return self.amount == other.amount

    def __ne__(self, other: "CurrencyAmount") -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: "CurrencyAmount") -> bool:
        self._check_currency(other.currency, "<")
        return self.amount < other.amount

    def __le__(self, other: "CurrencyAmount") -> bool:
        self._check_currency(other.currency, "<=")
        return self.amount <= other.amount

    def __gt__(self, other: "CurrencyAmount") -> bool:
        self._check_currency(other.currency, ">")
        return self.amount > other.amount

    def __ge__(self, other: "CurrencyAmount") -> bool:
        self._check_currency(other.currency, ">=")
        return self.amount >= other.amount

    def __add__(self, other: "CurrencyAmount") -> "CurrencyAmount":
        self._check_currency(other.currency, "+")
        return CurrencyAmount(self.amount + other.amount, self.currency)

    def __sub__(self, other: "CurrencyAmount") -> "CurrencyAmount":
        self._check_currency(other.currency, "-")
        return CurrencyAmount(self.amount - other.amount, self.currency)

    def __neg__(self) -> "CurrencyAmount":
        return CurrencyAmount(-self.amount, self.currency)

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency.value.upper()}"


def eur(amount: Decimal) -> CurrencyAmount:
    return CurrencyAmount(amount, Currency.EUR)


class BaseEvent(DomainEvent, domain="pricing"):
    class Config:
        arbitrary_types_allowed = True


class CustomerCreated(BaseEvent):
    name: str
    created: datetime
    reference: CustomerId
    currency: Currency

    def __str__(self) -> str:
        return f"Customer {self.name} created with {self.currency.value.upper()}"


class CustomerRenamed(BaseEvent):
    name: str
    old_name: str
    reference: CustomerId
    renamed: datetime

    def __str__(self) -> str:
        return f"Customer renamed from '{self.old_name}' to '{self.name}'"


class CustomerLocked(BaseEvent):
    reference: CustomerId
    reason: str

    def __str__(self) -> str:
        return f"Customer locked: {self.reason}"


class CustomerPaymentAdded(BaseEvent):
    reference: CustomerId
    payment_name: str
    payment: CurrencyAmount
    new_balance: CurrencyAmount
    transaction: int
    time_utc: datetime

    def __str__(self) -> str:
        return f"Added '{self.payment_name}' {self.payment} | Tx {self.transaction} => {self.new_balance}"


class CustomerChargeAdded(BaseEvent):
    reference: CustomerId
    charge_name: str
    charge: CurrencyAmount
    new_balance: CurrencyAmount
    transaction: int
    time_utc: datetime

    def __str__(self) -> str:
        return f"Charged '{self.charge_name}' {self.charge} | Tx {self.transaction} => {self.new_balance}"


class BaseCommand(DomainCommand, domain="pricing"):
    class Config:
        arbitrary_types_allowed = True


class CreateCustomer(BaseCommand):
    reference: CustomerId
    name: str
    currency: Currency

    def __str__(self) -> str:
        return f"Create {self.reference} named '{self.name}' with {self.currency.value.upper()}"


class RenameCustomer(BaseCommand):
    reference: CustomerId
    new_name: str

    def __str__(self) -> str:
        return f"Rename {self.reference} to '{self.new_name}'"


class LockCustomer(BaseCommand):
    reference: CustomerId
    reason: str


class LockCustomerForAccountOverdraft(BaseCommand):
    reference: CustomerId
    comment: str


class AddCustomerPayment(BaseCommand):
    reference: CustomerId
    name: str
    amount: CurrencyAmount

    def __str__(self) -> str:
        return f"Add {self.amount} - '{self.name}'"


class ChargeCustomer(BaseCommand):
    reference: CustomerId
    name: str
    amount: CurrencyAmount

    def __str__(self) -> str:
        return f"Charge {self.amount} - '{self.name}'"


class CustomerState(Entity):
    """Customer state built from events"""

    name: Optional[str] = None
    created: bool = False
    consumption_locked: bool = False
    manual_billing: bool = False
    currency: Optional[Currency] = None
    balance: Optional[CurrencyAmount] = None
    max_transaction_id: int = 0

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_events(cls, events: List[IEvent]) -> "CustomerState":
        state = cls()
        for event in events:
            state.mutate(event)
        return state

    @singledispatchmethod
    def mutate(self, event: IEvent) -> None:
        """Apply event to state using dynamic dispatch"""
        raise NotImplementedError()

    @mutate.register
    def when_customer_created(self, event: CustomerCreated) -> None:
        self._reference = event.reference
        self.created = True
        self.name = event.name
        self.currency = event.currency
        self.balance = CurrencyAmount(Decimal("0"), event.currency)

    @mutate.register
    def when_customer_renamed(self, event: CustomerRenamed) -> None:
        self.name = event.name

    @mutate.register
    def when_customer_locked(self, event: CustomerLocked) -> None:
        self.consumption_locked = True

    @mutate.register
    def when_customer_payment_added(self, event: CustomerPaymentAdded) -> None:
        self.balance = event.new_balance
        self.max_transaction_id = event.transaction

    @mutate.register
    def when_customer_charge_added(self, event: CustomerChargeAdded) -> None:
        self.balance = event.new_balance
        self.max_transaction_id = event.transaction


class Customer(ESRootEntity):
    _state: CustomerState

    @classmethod
    def create(
        cls, reference: CustomerId, name: str, currency: Currency, pricing_service: IPricingService
    ) -> "Customer":
        self = cls(__reference__=reference)
        self._state = CustomerState()
        self.trigger_event(
            CustomerCreated, name=name, created=datetime.utcnow(), reference=reference, currency=currency
        )

        bonus = pricing_service.get_welcome_bonus(currency)
        self.add_payment("Welcome bonus", bonus)
        return self

    @classmethod
    def from_events(cls, reference: IdType, events: t.Iterable[IEvent]) -> "Customer":
        self = cls(__reference__=reference)
        self._events.extend(events)
        self._state = CustomerState.from_events(self._events)
        return self

    def when(self, event: IEvent) -> None:
        self._state.mutate(event)

    def rename(self, name: str) -> None:
        if self._state.name == name:
            return

        self.trigger_event(
            CustomerRenamed,
            name=name,
            reference=self._state.__reference__,
            old_name=self._state.name,
            renamed=datetime.utcnow(),
        )

    def lock_customer(self, reason: str) -> None:
        if self._state.consumption_locked:
            return

        self.trigger_event(CustomerLocked, reference=self._state.reference, reason=reason)

    def lock_for_account_overdraft(self, comment: str, pricing_service: IPricingService) -> None:
        if self._state.manual_billing:
            return

        threshold = pricing_service.get_overdraft_threshold(self._state.currency)
        if self._state.balance < threshold:
            self.lock_customer(f"Overdraft. {comment}")

    def add_payment(self, name: str, amount: CurrencyAmount) -> None:
        self.trigger_event(
            CustomerPaymentAdded,
            reference=self._state.__reference__,
            payment=amount,
            new_balance=self._state.balance + amount,
            payment_name=name,
            transaction=self._state.max_transaction_id + 1,
            time_utc=datetime.utcnow(),
        )

    def charge(self, name: str, amount: CurrencyAmount) -> None:
        self.trigger_event(
            CustomerChargeAdded,
            reference=self._state.__reference__,
            charge=amount,
            new_balance=self._state.balance - amount,
            charge_name=name,
            transaction=self._state.max_transaction_id + 1,
            time_utc=datetime.utcnow(),
        )


class SimplePricingService(IPricingService):
    """Simple pricing service implementation"""

    def get_welcome_bonus(self, currency: Currency) -> CurrencyAmount:
        bonuses = {
            Currency.EUR: CurrencyAmount(Decimal("10"), Currency.EUR),
            Currency.USD: CurrencyAmount(Decimal("12"), Currency.USD),
            Currency.RUR: CurrencyAmount(Decimal("500"), Currency.RUR),
        }
        return bonuses.get(currency, CurrencyAmount(Decimal("0"), currency))

    def get_overdraft_threshold(self, currency: Currency) -> CurrencyAmount:
        thresholds = {
            Currency.EUR: CurrencyAmount(Decimal("-100"), Currency.EUR),
            Currency.USD: CurrencyAmount(Decimal("-120"), Currency.USD),
            Currency.RUR: CurrencyAmount(Decimal("-5000"), Currency.RUR),
        }
        return thresholds.get(currency, CurrencyAmount(Decimal("0"), currency))


def test_example():
    pricing_service = SimplePricingService()

    customer_id = CustomerId(1)
    customer = Customer.create(customer_id, "John Doe", Currency.EUR, pricing_service)

    customer.add_payment("Initial deposit", CurrencyAmount(Decimal("100"), Currency.EUR))

    customer.charge("Service fee", CurrencyAmount(Decimal("20"), Currency.EUR))

    customer.rename("John Smith")

    events = customer.collect_events()
    print("Events generated:")
    for event in events:
        print(f"- {event}")

    new = Customer.from_events(reference=customer_id, events=events)

    assert new == customer
