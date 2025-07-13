from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import singledispatchmethod
from typing import List, Protocol, Optional
from decimal import Decimal
import typing as t

from pyddd.domain import RootEntity

# Example from V.Vernon's book "Implementing Domain-Driven Design" implemented in Python


class IIdentity(Protocol):
    """Protocol for identity objects"""

    pass


class IEvent(Protocol):
    """Protocol for events"""

    pass


class ICommand(Protocol):
    """Protocol for commands"""

    pass


class IPricingService(Protocol):
    """Protocol for pricing service"""

    def get_welcome_bonus(self, currency: "Currency") -> "CurrencyAmount": ...

    def get_overdraft_threshold(self, currency: "Currency") -> "CurrencyAmount": ...


# Domain types
@dataclass(frozen=True)
class CustomerId:
    """Customer identity value object"""

    id: int

    def __str__(self) -> str:
        return f"customer-{self.id}"


class Currency(Enum):
    """Currency enumeration"""

    NONE = "none"
    EUR = "eur"
    USD = "usd"
    RUR = "rur"


@dataclass(frozen=True)
class CurrencyAmount:
    """Currency amount value object with operator overloading"""

    amount: Decimal
    currency: Currency

    def __post_init__(self):
        # Ensure amount is Decimal for precision
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))

    def _check_currency(self, other_currency: Currency, operation: str) -> None:
        """Check if currencies match for operations"""
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
    """Create EUR currency amount"""
    return CurrencyAmount(amount, Currency.EUR)


# Events
@dataclass
class CustomerCreated:
    """Customer created event"""

    name: str
    created: datetime
    reference: CustomerId
    currency: Currency

    def __str__(self) -> str:
        return f"Customer {self.name} created with {self.currency.value.upper()}"


@dataclass
class CustomerRenamed:
    """Customer renamed event"""

    name: str
    old_name: str
    reference: CustomerId
    renamed: datetime

    def __str__(self) -> str:
        return f"Customer renamed from '{self.old_name}' to '{self.name}'"


@dataclass
class CustomerLocked:
    """Customer locked event"""

    reference: CustomerId
    reason: str

    def __str__(self) -> str:
        return f"Customer locked: {self.reason}"


@dataclass
class CustomerPaymentAdded:
    """Customer payment added event"""

    reference: CustomerId
    payment_name: str
    payment: CurrencyAmount
    new_balance: CurrencyAmount
    transaction: int
    time_utc: datetime

    def __str__(self) -> str:
        return f"Added '{self.payment_name}' {self.payment} | Tx {self.transaction} => {self.new_balance}"


@dataclass
class CustomerChargeAdded:
    """Customer charge added event"""

    reference: CustomerId
    charge_name: str
    charge: CurrencyAmount
    new_balance: CurrencyAmount
    transaction: int
    time_utc: datetime

    def __str__(self) -> str:
        return f"Charged '{self.charge_name}' {self.charge} | Tx {self.transaction} => {self.new_balance}"


# Commands
@dataclass
class CreateCustomer:
    """Create customer command"""

    reference: CustomerId
    name: str
    currency: Currency

    def __str__(self) -> str:
        return f"Create {self.reference} named '{self.name}' with {self.currency.value.upper()}"


@dataclass
class RenameCustomer:
    """Rename customer command"""

    reference: CustomerId
    new_name: str

    def __str__(self) -> str:
        return f"Rename {self.reference} to '{self.new_name}'"


@dataclass
class LockCustomer:
    """Lock customer command"""

    reference: CustomerId
    reason: str


@dataclass
class LockCustomerForAccountOverdraft:
    """Lock customer for account overdraft command"""

    reference: CustomerId
    comment: str


@dataclass
class AddCustomerPayment:
    """Add customer payment command"""

    reference: CustomerId
    name: str
    amount: CurrencyAmount

    def __str__(self) -> str:
        return f"Add {self.amount} - '{self.name}'"


@dataclass
class ChargeCustomer:
    """Charge customer command"""

    reference: CustomerId
    name: str
    amount: CurrencyAmount

    def __str__(self) -> str:
        return f"Charge {self.amount} - '{self.name}'"


@dataclass(kw_only=True, eq=True)
class CustomerState:
    """Customer state built from events"""

    reference: Optional[CustomerId] = None
    name: Optional[str] = None
    created: bool = False
    consumption_locked: bool = False
    manual_billing: bool = False
    currency: Optional[Currency] = None
    balance: Optional[CurrencyAmount] = None
    max_transaction_id: int = 0

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
        """Handle customer created event"""
        self.created = True
        self.name = event.name
        self.reference = event.reference
        self.currency = event.currency
        self.balance = CurrencyAmount(Decimal("0"), event.currency)

    @mutate.register
    def when_customer_renamed(self, event: CustomerRenamed) -> None:
        """Handle customer renamed event"""
        self.name = event.name

    @mutate.register
    def when_customer_locked(self, event: CustomerLocked) -> None:
        """Handle customer locked event"""
        self.consumption_locked = True

    @mutate.register
    def when_customer_payment_added(self, event: CustomerPaymentAdded) -> None:
        """Handle customer payment added event"""
        self.balance = event.new_balance
        self.max_transaction_id = event.transaction

    @mutate.register
    def when_customer_charge_added(self, event: CustomerChargeAdded) -> None:
        """Handle customer charge added event"""
        self.balance = event.new_balance
        self.max_transaction_id = event.transaction


class Customer(RootEntity):
    """Customer aggregate root"""

    _state: CustomerState

    def _apply(self, event: IEvent) -> None:
        """Apply event to state and add to changes"""
        self._state.mutate(event)
        self._events.append(event)

    @classmethod
    def create(
        cls, reference: CustomerId, name: str, currency: Currency, pricing_service: IPricingService
    ) -> "Customer":
        """Create customer"""
        self = cls()
        self._state = CustomerState()
        self._apply(CustomerCreated(name=name, created=datetime.utcnow(), reference=reference, currency=currency))

        # Add welcome bonus
        bonus = pricing_service.get_welcome_bonus(currency)
        self.add_payment("Welcome bonus", bonus)
        return self

    @classmethod
    def from_events(cls, events: t.Iterable[IEvent]) -> "Customer":
        """Rehydrate customer from events"""
        self = cls()
        self._events.extend(events)
        self._state = CustomerState.from_events(self._events)
        return self

    def rename(self, name: str) -> None:
        """Rename customer"""
        if self._state.name == name:
            return

        self._apply(
            CustomerRenamed(
                name=name, reference=self._state.reference, old_name=self._state.name, renamed=datetime.utcnow()
            )
        )

    def lock_customer(self, reason: str) -> None:
        """Lock customer"""
        if self._state.consumption_locked:
            return

        self._apply(CustomerLocked(reference=self._state.reference, reason=reason))

    def lock_for_account_overdraft(self, comment: str, pricing_service: IPricingService) -> None:
        """Lock customer for account overdraft"""
        if self._state.manual_billing:
            return

        threshold = pricing_service.get_overdraft_threshold(self._state.currency)
        if self._state.balance < threshold:
            self.lock_customer(f"Overdraft. {comment}")

    def add_payment(self, name: str, amount: CurrencyAmount) -> None:
        """Add payment to customer"""
        self._apply(
            CustomerPaymentAdded(
                reference=self._state.reference,
                payment=amount,
                new_balance=self._state.balance + amount,
                payment_name=name,
                transaction=self._state.max_transaction_id + 1,
                time_utc=datetime.utcnow(),
            )
        )

    def charge(self, name: str, amount: CurrencyAmount) -> None:
        """Charge customer"""
        self._apply(
            CustomerChargeAdded(
                reference=self._state.reference,
                charge=amount,
                new_balance=self._state.balance - amount,
                charge_name=name,
                transaction=self._state.max_transaction_id + 1,
                time_utc=datetime.utcnow(),
            )
        )

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._state == getattr(other, "_state")


# Example pricing service implementation
class SimplePricingService:
    """Simple pricing service implementation"""

    def get_welcome_bonus(self, currency: Currency) -> CurrencyAmount:
        """Get welcome bonus for currency"""
        bonuses = {
            Currency.EUR: CurrencyAmount(Decimal("10"), Currency.EUR),
            Currency.USD: CurrencyAmount(Decimal("12"), Currency.USD),
            Currency.RUR: CurrencyAmount(Decimal("500"), Currency.RUR),
        }
        return bonuses.get(currency, CurrencyAmount(Decimal("0"), currency))

    def get_overdraft_threshold(self, currency: Currency) -> CurrencyAmount:
        """Get overdraft threshold for currency"""
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

    # Add payment
    customer.add_payment("Initial deposit", CurrencyAmount(Decimal("100"), Currency.EUR))

    # Charge customer
    customer.charge("Service fee", CurrencyAmount(Decimal("20"), Currency.EUR))

    # Rename customer
    customer.rename("John Smith")

    events = customer.collect_events()
    print("Events generated:")
    for event in events:
        print(f"- {event}")

    new = Customer.from_events(events)

    assert new == customer
