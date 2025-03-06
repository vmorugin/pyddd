import abc
import dataclasses
import datetime as dt
import uuid

from pyddd.application import (
    Module,
    Application,
)
from pyddd.application import (
    Equal,
    Not,
)
from pyddd.domain import (
    DomainCommand,
    DomainEvent,
)
from pyddd.domain.entity import (
    RootEntity,
    IRootEntity,
)
from pyddd.domain.event import IEvent

product_domain = 'product'


class Product(RootEntity):
    def __init__(self, sku: str, price: int):
        self.sku = sku
        self.price = price

    @classmethod
    def create(cls, sku: str, price: int):
        product = Product(sku, price=price)
        product.register_event(ProductCreated(reference=str(product.__reference__), price=price))
        return product


class CreateProduct(DomainCommand, domain=product_domain):
    sku: str
    price: int


class ProductCreated(DomainEvent, domain=product_domain):
    reference: str
    price: int


class PrintCreatedZeroPriceInfo(DomainCommand, domain=product_domain):
    reference: str
    price: int

class PrintCreatedProductInfo(DomainCommand, domain=product_domain):
    reference: str
    price: int


module = Module(product_domain)


class IRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, entity: IRootEntity):
        ...


class IProductRepository(IRepository, abc.ABC):
    ...


@module.register
def create_product(cmd: CreateProduct, repository: IProductRepository):
    product = Product.create(cmd.sku, cmd.price)
    repository.save(product)
    return product.__reference__


@module.subscribe(ProductCreated.__topic__, condition=Equal(price=0))
@module.register
def create_product_without_price(cmd: PrintCreatedZeroPriceInfo):
    print(f"Product {cmd.reference} was created with zero price!")


@module.subscribe(ProductCreated.__topic__, condition=Not(Equal(price=0)))
@module.register
def create_product_without_price(cmd: PrintCreatedProductInfo):
    print(f"Product {cmd.reference} was created.")


@dataclasses.dataclass(kw_only=True)
class StoredEvent:
    id: str
    occurred_on: dt.datetime
    event_name: str
    payload: str


class IEventStore(abc.ABC):
    @abc.abstractmethod
    def insert(self, event: StoredEvent):
        ...


class IEventSubscriber(abc.ABC):

    @abc.abstractmethod
    def notify(self, event: IEvent):
        ...


class IEventPublisher(abc.ABC):
    @abc.abstractmethod
    def publish(self, *events: IEvent):
        ...

    @abc.abstractmethod
    def subscribe(self, subscriber: IEventSubscriber):
        ...


class InMemoryEventStore(IEventStore):
    def __init__(self, memory: list[StoredEvent]):
        self._memory = memory

    def insert(self, event: StoredEvent):
        self._memory.append(event)


class EventPublisher(IEventPublisher):
    def __init__(self):
        self._event_listeners: list[IEventSubscriber] = []

    def publish(self, *events: IEvent):
        for event in events:
            for listener in self._event_listeners:
                listener.notify(event)

    def subscribe(self, subscriber: IEventSubscriber):
        self._event_listeners.append(subscriber)


class EventStoreListener(IEventSubscriber):

    def __init__(self, event_store: IEventStore):
        self._event_store = event_store

    def notify(self, event: IEvent):
        stored_event = StoredEvent(
            id=str(uuid.uuid4()),
            occurred_on=event.occurred_on,
            event_name=event.__topic__,
            payload=event.to_json(),
        )
        self._event_store.insert(stored_event)


class ApplicationHandlerListener(IEventSubscriber):

    def __init__(self, application: Application):
        self._app = application

    def notify(self, event: IEvent):
        self._app.handle(event)


class ImMemoryProductRepository(IProductRepository):
    def __init__(self, memory: {}, publisher: IEventPublisher):
        self._memory = memory
        self._publisher = publisher

    def save(self, entity: IRootEntity):
        self._memory[entity.__reference__] = entity
        self._publisher.publish(*entity.collect_events())


def test():
    app = Application()
    app.include(module)

    stored_memory = []
    event_store = InMemoryEventStore(stored_memory)
    event_store_listener = EventStoreListener(event_store)

    app_message_listener = ApplicationHandlerListener(app)

    publisher = EventPublisher()
    publisher.subscribe(event_store_listener)
    publisher.subscribe(app_message_listener)

    repository_memory = {}
    app.set_defaults(product_domain, repository=ImMemoryProductRepository(repository_memory, publisher=publisher))

    app.run()

    product_1 = app.handle(CreateProduct(sku='123', price=123))
    product_2 = app.handle(CreateProduct(sku='123', price=0))  # will not be printed because of zero price

    assert len(stored_memory) == 2

    assert isinstance(repository_memory[product_1], Product)
    assert isinstance(repository_memory[product_2], Product)
