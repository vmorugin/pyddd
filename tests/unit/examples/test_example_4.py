import abc
import asyncio
import random
import datetime as dt

from pyddd.application import (
    Module,
    Application,
    get_application,
    set_application,
)
from pyddd.domain import (
    DomainCommand,
    DomainEvent,
    DomainName,
)
from pyddd.domain.entity import (
    RootEntity,
)

__product_domain__ = DomainName("async.products")


class ProductCreated(DomainEvent, domain=__product_domain__):
    reference: str


class Product(RootEntity):
    sku: str
    price: int
    stock: int

    @classmethod
    def create(cls, sku: str):
        product = Product(sku=sku, price=0, stock=0)
        product.register_event(ProductCreated(reference=str(product.__reference__)))
        return product

    def renew_price(self, price: int):
        self.price = price

    def update_stock(self, stock: int):
        self.stock = stock


class CreateProduct(DomainCommand, domain=__product_domain__):
    sku: str


class ActualizeProduct(DomainCommand, domain=__product_domain__):
    product_id: str


module = Module(__product_domain__)


class IRepository(abc.ABC):
    @abc.abstractmethod
    async def save(self, entity: Product): ...

    @abc.abstractmethod
    async def get(self, entity_id: str) -> Product: ...


class IProductRepository(IRepository, abc.ABC): ...


@module.register
async def create_product(cmd: CreateProduct, repository: IProductRepository):
    product = Product.create(cmd.sku)
    await repository.save(product)
    return product.__reference__


class IProductStorageAdapter(abc.ABC):
    @abc.abstractmethod
    async def get_price(self, sku: str) -> int: ...

    @abc.abstractmethod
    async def get_stock(self, sku: str) -> int: ...


class ImMemoryProductRepository(IProductRepository):
    def __init__(self, memory: {}):
        self._memory = memory

    async def save(self, entity: Product):
        self._memory[str(entity.__reference__)] = entity
        app = get_application()
        for event in entity.collect_events():
            app.handle(event)

    async def get(self, entity_id: str) -> Product:
        return self._memory[entity_id]


class PriceAdapter(IProductStorageAdapter):
    async def get_price(self, sku: str) -> int:
        print(f"Price requested for {sku=} at {dt.datetime.now()}...")
        await asyncio.sleep(0.01)
        print(f"Got price response at {dt.datetime.now()}")
        return random.randint(1, 100)

    async def get_stock(self, sku: str) -> int:
        print(f"Stock requested for {sku=} at {dt.datetime.now()}...")
        await asyncio.sleep(0.01)
        print(f"Got stock response at {dt.datetime.now()}")
        return random.randint(1, 5)


@module.subscribe(str(ProductCreated.__topic__), converter=lambda x: {"product_id": str(x["reference"])})
@module.register
async def actualize_product(
    cmd: ActualizeProduct,
    repository: IProductRepository,
    price_adapter: IProductStorageAdapter,
):
    product = await repository.get(cmd.product_id)
    new_price, new_stock = await asyncio.gather(
        price_adapter.get_price(product.sku), price_adapter.get_stock(product.sku)
    )
    product.renew_price(new_price)
    product.update_stock(new_stock)
    await repository.save(product)


async def test():
    app = Application()
    app.include(module)
    repository = ImMemoryProductRepository({})
    app.set_defaults(__product_domain__, repository=repository, price_adapter=PriceAdapter())
    set_application(app)
    await app.run_async()

    product_id = await app.handle(CreateProduct(sku="AB123CD"))

    product = await repository.get(str(product_id))
    assert product.price == 0
    assert product.stock == 0

    await asyncio.sleep(0.02)

    assert product.price != 0
    assert product.stock != 0
    await app.stop_async()
