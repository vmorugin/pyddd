[![Coverage Status](https://coveralls.io/repos/github/vmorugin/pyddd/badge.svg?branch=master)](https://coveralls.io/github/vmorugin/pyddd?branch=master) [![PyPI - License](https://img.shields.io/pypi/l/pyddd)](https://pypi.org/project/pyddd) [![PyPI](https://img.shields.io/pypi/v/pyddd)](https://pypi.org/project/pyddd) [![PyPI](https://img.shields.io/pypi/pyversions/pyddd)](https://pypi.org/project/pyddd) [![Mypy](http://www.mypy-lang.org/static/mypy_badge.svg)]()

# PyDDD - Domain-Driven Design для Python

PyDDD - это библиотека для реализации Domain-Driven Design (DDD) паттернов в Python с поддержкой как синхронного, 
так и асинхронного выполнения.

## Основные возможности

- 🏗️ **Domain Entities & Aggregates** - Создание доменных сущностей и агрегатов
- 📨 **Commands & Events** - Система команд и событий
- 🔧 **Dependency Injection** - Встроенная система внедрения зависимостей
- 🔄 **Event Sourcing** - Поддержка событийного подхода
- ⚡ **Async Support** - Полная поддержка асинхронного выполнения
- 🎯 **Event Filtering** - Условная обработка событий
- 🗃️ **Unit of Work** - Паттерн Unit of Work для управления транзакциями

## Установка

```bash
pip install pyddd
```

## Быстрый старт

### Базовый пример

```python
import abc
from pyddd.application import Module,
    Application
from pyddd.domain import DomainCommand,
    DomainEvent
from pyddd.domain.entity import RootEntity


class CreatePet(DomainCommand, domain="pet"):
    name: str


class PetCreated(DomainEvent, domain="pet"):
    pet_id: str
    name: str


class Pet(RootEntity):
    name: str

    @classmethod
    def create(cls, name: str):
        pet = cls(name=name)
        pet.register_event(PetCreated(name=name, pet_id=str(pet.__reference__)))
        return pet


pet_module = Module("pet")


class IPetRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, pet: Pet):
        ...
    
    @abc.abstractmethod
    def get(self, pet_id: str) -> Pet:
        ...


@pet_module.register
def create_pet(cmd: CreatePet, repository: IPetRepository):
    pet = Pet.create(cmd.name)
    repository.save(pet)
    return pet.__reference__


app = Application()
app.include(pet_module)
app.set_defaults("pet", repository=InMemoryPetRepository({}))
app.run()

# Выполняем команду
pet_id = app.handle(CreatePet(name="Fluffy"))
```

## Основные концепции

### Доменные команды

Команды представляют намерения изменить состояние системы:

```python
class CreateProduct(DomainCommand, domain="product"):
    sku: str
    price: int

class UpdatePrice(DomainCommand, domain="product"):
    product_id: str
    new_price: int
```

### Доменные события

События уведомляют о произошедших изменениях. Имя события состоит из действия в прошедшем времени.

```python
class ProductCreated(DomainEvent, domain="product"):
    reference: str
    price: int

class PriceUpdated(DomainEvent, domain="product"):
    product_id: str
    old_price: int
    new_price: int
```

### Агрегаты

Агрегаты инкапсулируют бизнес-логику и генерируют события:

```python
class Product(RootEntity):
    sku: str
    price: int

    @classmethod
    def create(cls, sku: str, price: int):
        product = cls(sku=sku, price=price)
        product.register_event(ProductCreated(
            reference=str(product.__reference__), 
            price=price
        ))
        return product

    def update_price(self, new_price: int):
        old_price = self.price
        self.price = new_price
        self.register_event(PriceUpdated(
            product_id=str(self.__reference__),
            old_price=old_price,
            new_price=new_price
        ))
```

### Подписка на события

Вы можете подписываться на события. Все события будут преобразованы в команду. 

```python
greet_module = Module("greet")

@greet_module.subscribe("pet.PetCreated")
@greet_module.register
def register_pet(cmd: CreateGreetLogCommand, repository: IPetGreetRepo):
    journal = PerGreetJournal.create(pet_id=cmd.pet_id, pet_name=cmd.name)
    repository.save(journal)
    return journal.__reference__
```

### Условная обработка событий

Можно добавлять условия для обработки событий:

```python
from pyddd.application import Equal, Not
from pyddd.domain.command import DomainCommand


class HandleFreeProductCommand(DomainCommand, domain='statistics'):
    reference: str

    
class HandlePaidProductCommand(DomainCommand, domain='statistics'):
    reference: str
    amount: int


@module.subscribe('product.ProductCreated', condition=Equal(price=0))
@module.register
def handle_free_product(cmd: HandleFreeProductCommand):
    print(f"Free product created: {cmd.reference} without price")


@module.subscribe('product.ProductCreated', condition=Not(Equal(price=0)))
@module.register
def handle_paid_product(cmd: HandlePaidProductCommand):
    print(f"Paid product created: {cmd.reference} with price {cmd.price}")
```

## Асинхронная поддержка

PyDDD полностью поддерживает асинхронное выполнение:

```python
from pyddd.application import AsyncExecutor

# Асинхронные обработчики
@pet_module.register
async def create_pet_async(cmd: CreatePet, repository: IPetRepository):
    pet = Pet.create(cmd.name)
    await repository.save(pet)
    return pet.__reference__

# Настройка асинхронного приложения
app = Application(executor=AsyncExecutor())
app.include(pet_module)

await app.run_async()
pet_id = await app.handle(CreatePet(name="Fluffy"))
```

### Конвертеры событий

Для преобразования данных событий в команды:

```python
@greet_module.subscribe(
    "pet.PetCreated", 
    converter=lambda x: {"pet_id": x["reference"], "name": x["name"]}
)
@greet_module.register
async def record_log(cmd: CreateGreetLogCommand):
    print("Created greet log for pet:", cmd.pet_id)
    
```

## Unit of Work

Для управления транзакциями используется паттерн Unit of Work:

```python
from pyddd.infrastructure.persistence.abstractions import IUnitOfWorkBuilder

@module.register
async def create_workspace(
    cmd: CreateWorkspace, 
    uow_builder: IUnitOfWorkBuilder[IWorkspaceRepoFactory]
) -> WorkspaceId:
    with uow_builder() as uow:
        tenant_repo = uow.repository.tenant()
        project_repo = uow.repository.project()
        workspace_repo = uow.repository.workspace()
        
        tenant = tenant_repo.create(name=cmd.tenant_name)
        project = project_repo.create(name=cmd.project_name, tenant_id=tenant.__reference__)
        workspace = workspace_repo.create(tenant=tenant, project=project)
        
        uow.apply()  # Применяем все изменения в рамках транзакции
    
    return workspace.__reference__
```

## Внедрение зависимостей

PyDDD автоматически внедряет зависимости в обработчики команд:

```python
# Настройка зависимостей по умолчанию
app.set_defaults("product", 
    repository=ProductRepository(),
    price_adapter=PriceAdapter(),
    notification_service=EmailService()
)

# Автоматическое внедрение в обработчик
@module.register
async def update_product_price(
    cmd: UpdateProductPrice,
    repository: IProductRepository,  # Автоматически внедряется
    price_adapter: IPriceAdapter,    # Автоматически внедряется
):
    product = await repository.get(cmd.product_id)
    new_price = await price_adapter.get_current_price(product.sku)
    product.update_price(new_price)
    await repository.save(product)
```

## Лучшие практики

### 1. Разделение доменов

Организуйте код по доменам и создавайте отдельные модули:

```python
# Домен продуктов
product_module = Module("product")

# Домен заказов  
order_module = Module("order")

# Домен клиентов
customer_module = Module("customer")
```

### 2. Слабая связанность

Используйте события для связи между доменами вместо прямых вызовов:

```python
# Вместо прямого вызова
def create_order(cmd: CreateOrder):
    order = Order.create(...)
    # НЕ ДЕЛАЙТЕ ТАК: customer_service.notify_order_created(order)


# Используйте события
def create_order(cmd: CreateOrder):
    order = Order.create(...)
    order.register_event(OrderCreated(order_id=str(order.__reference__)))
```

### 3. Небольшие транзакции

Избегайте изменения нескольких агрегатов в одной транзакции:

```python
# Предпочтительно - одна команда, один агрегат
@module.register
async def create_product(cmd: CreateProduct, repository: IProductRepository):
    product = Product.create(cmd.sku, cmd.price)
    await repository.save(product)
    return product.__reference__
```

## Примеры использования

### Система управления товарами

```python
# Команды
class CreateProduct(DomainCommand, domain="product"):
    sku: str
    price: int

class UpdateStock(DomainCommand, domain="product"):
    product_id: str
    quantity: int

# События
class ProductCreated(DomainEvent, domain="product"):
    product_id: str
    sku: str

class StockUpdated(DomainEvent, domain="product"):
    product_id: str
    new_quantity: int

# Агрегат
class Product(RootEntity):
    sku: str
    price: int
    stock: int

    @classmethod
    def create(cls, sku: str, price: int):
        product = cls(sku=sku, price=price, stock=0)
        product.register_event(ProductCreated(
            product_id=str(product.__reference__), 
            sku=sku
        ))
        return product

    def update_stock(self, quantity: int):
        self.stock = quantity
        self.register_event(StockUpdated(
            product_id=str(self.__reference__),
            new_quantity=quantity
        ))
```

### Система уведомлений

```python
notification_module = Module("notification")

@notification_module.subscribe("product.ProductCreated")
@notification_module.register
async def notify_product_created(cmd: NotifyProductCreatedCommand, email_service: IEmailService):
    await email_service.send_notification(
        subject="Новый товар создан",
        message=f"Товар {cmd.sku} добавлен в каталог"
    )
```

## Заключение

PyDDD предоставляет мощные инструменты для реализации чистой архитектуры и Domain-Driven Design паттернов в Python. 
Библиотека поддерживает как синхронное, так и асинхронное выполнение, обеспечивая гибкость в различных сценариях 
использования.

Для получения дополнительной информации и примеров обратитесь к тестам в директории `tests/unit/examples/`.
