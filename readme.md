# pyddd

`pyddd` - это DDD (Domain-Driven Design) фреймворк для Python, предоставляющий встроенный менеджер зависимостей и шину сообщений. Он упрощает построение сложных доменных моделей и событийное программирование.

## Возможности

- **Разделение доменов** через `Module`
- **Использование команд и событий** (`DomainCommand`, `DomainEvent`)
- **Корневые сущности (`RootEntity`)** и управление идентификаторами (`EntityId`)
- **Встроенный менеджер зависимостей**
- **Событийно-ориентированная архитектура**

## Установка

На данный момент `pyddd` не опубликован в PyPI. Вы можете установить его из исходного кода:

```bash
pip install git+https://github.com/vmorugin/pyddd.git
```

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
        pet.register_event(PetCreated(name=name, pet_id=pet.reference))
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
    return pet.reference
```

### Запуск приложения

```python
from application.application import get_application, set_application

class InMemoryPetRepo(IPetRepository):
    def __init__(self):
        self.memory = {}
    
    def get(self, name: str) -> Pet:
        return self.memory.get(name)
    
    def save(self, entity: Pet):
        self.memory[entity.name] = entity

# Настройка приложения
app = Application()
app.include(pet_module)
app.set_defaults('pet', repository=InMemoryPetRepo())
set_application(app)

# Использование
fluff_id = app.handle(CreatePet(name='Fluff'))
print(f'Создан питомец с ID: {fluff_id}')
```

## Лицензия

Этот проект распространяется под лицензией MIT. Подробности см. в файле LICENSE.

## Контрибьюция

Мы приветствуем ваш вклад! Создавайте issue, присылайте pull request'ы и помогайте развивать `pyddd`.

## Контакты

Если у вас есть вопросы или предложения, свяжитесь с нами через GitHub Issues.

