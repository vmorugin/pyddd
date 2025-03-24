[![Coverage Status](https://coveralls.io/repos/github/vmorugin/ddd-python/badge.svg?branch=master)](https://coveralls.io/github/vmorugin/ddd-python?branch=master) [![PyPI - License](https://img.shields.io/pypi/l/ddd-python)](https://pypi.org/project/ddd-python) [![PyPI](https://img.shields.io/pypi/v/ddd-python)](https://pypi.org/project/ddd-python) [![PyPI](https://img.shields.io/pypi/pyversions/ddd-python)](https://pypi.org/project/ddd-python) [![Mypy](http://www.mypy-lang.org/static/mypy_badge.svg)]()

# pyddd

`pyddd` - это DDD (Domain-Driven Design) фреймворк для Python, предоставляющий встроенный менеджер зависимостей и шину
сообщений. Он упрощает построение сложных доменных моделей и событийное программирование.

## Возможности

- **Разделение доменов** через `Module`
- **Использование команд и событий** (`DomainCommand`, `DomainEvent`)
- **Корневые сущности (`RootEntity`)** и управление идентификаторами (`EntityId`)
- **Встроенный менеджер зависимостей**
- **Событийно-ориентированная архитектура**

## Быстрый старт

### Определение доменной модели

```python
class PetCreated(DomainEvent, domain='pet'):
    pet_id: str
    name: str


class Pet(RootEntity):
    def __init__(self, name: str):
        self.name = name

    @classmethod
    def create(cls, name: str):
        pet = cls(name)
        pet.register_event(PetCreated(name=name, pet_id=pet.__reference__))
        return pet
```

### Репозитории и модуль

```python
class IPetRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, entity: RootEntity):
        ...

    @abc.abstractmethod
    def get(self, name: str) -> Pet:
        ...


class CreatePet(DomainCommand, domain='pet'):
    name: str


pet_module = Module('pet')


@pet_module.register
def create_pet(cmd: CreatePet, repository: IPetRepository):
    pet = Pet.create(cmd.name)
    repository.save(pet)
    return pet.__reference__
```

### Запуск приложения

```python
class InMemoryPetRepo(IPetRepository):
    def __init__(self):
        self.memory = {}

    def get(self, name: str) -> Pet:
        return self.memory.get(name)

    def save(self, entity: Pet):
        self.memory[entity.name] = entity


# Настройка приложения
app = Application()
app.run()
app.include(pet_module)
app.set_defaults('pet', repository=InMemoryPetRepo())
set_application(app)

# Использование
fluff_id = app.handle(CreatePet(name='Fluff'))
print(f'Создан питомец с ID: {fluff_id}')
```

### Запуск интеграционных тестов:

```shell
# Поднимаем внешние сервисы
docker-compose up -d

# Запуск тестов
pytest tests
```

## Лицензия

Этот проект распространяется под лицензией MIT. Подробности см. в файле LICENSE.

## Контрибьюция

Мы приветствуем ваш вклад! Создавайте issue, присылайте pull request'ы и помогайте развивать `pyddd`.

## Контакты

Если у вас есть вопросы или предложения, свяжитесь с нами через GitHub Issues.

