[![Coverage Status](https://coveralls.io/repos/github/vmorugin/ddd-python/badge.svg?branch=master)](https://coveralls.io/github/vmorugin/ddd-python?branch=master) [![PyPI - License](https://img.shields.io/pypi/l/ddd-python)](https://pypi.org/project/ddd-python) [![PyPI](https://img.shields.io/pypi/v/ddd-python)](https://pypi.org/project/ddd-python) [![PyPI](https://img.shields.io/pypi/pyversions/ddd-python)](https://pypi.org/project/ddd-python) [![Mypy](http://www.mypy-lang.org/static/mypy_badge.svg)]()

# pyddd

`pyddd` - это DDD (Domain-Driven Design) фреймворк для Python, предоставляющий встроенный менеджер зависимостей и шину
сообщений. Он упрощает построение сложных доменных моделей и событийное программирование.

## Возможности

- **Разделение доменов** через `Module`
- **Использование команд и событий** (`DomainCommand`, `DomainEvent`)
- **Корневые сущности (`RootEntity`)**
- **Встроенный менеджер зависимостей**
- **Событийно-ориентированная архитектура**
- **Транспорт для работы с событиями**
- **Базовый `Unit Of Work` и репозиторий**

## Локальная установка зависимостей

Нужно установить poetry и все зависимости.
Запуск тестов через pytest
```bash
pip install uv
uv install --all-extras

pytest .
```

## Быстрый старт

```python
import abc
from pyddd.domain import RootEntity, DomainEvent, DomainCommand, DomainName
from pyddd.application import Module, Application, set_application

# Определение домена

__domain__ = DomainName('pet')

class PetCreated(DomainEvent, domain=__domain__):
    pet_id: str
    name: str

class Pet(RootEntity):
    name: str

    @classmethod
    def create(cls, name: str):
        pet = cls(name=name)
        pet.register_event(PetCreated(name=name, pet_id=pet.__reference__))
        return pet

# Репозитории и модуль
class IPetRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, entity: RootEntity):
        ...

    @abc.abstractmethod
    def get(self, name: str) -> Pet:
        ...


class CreatePet(DomainCommand, domain=__domain__):
    name: str


pet_module = Module(__domain__)


@pet_module.register
def create_pet(cmd: CreatePet, repository: IPetRepository):
    pet = Pet.create(cmd.name)
    repository.save(pet)
    return pet.__reference__

# Запуск приложения
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

# Работа с юзкейсами через команды и шину приложения
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

