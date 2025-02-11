import abc
import asyncio
import logging
import uuid
from uuid import NAMESPACE_URL

from pyddd.application import (
    Module,
    Application,
)
from pyddd.application import (
    get_application,
    set_application,
)
from pyddd.application import AsyncExecutor
from domain import (
    IRootEntity,
    DomainCommand,
    DomainEvent,
)
from pyddd.domain.entity import RootEntity


class CreatePet(DomainCommand, domain='pet'):
    name: str


class PetCreated(DomainEvent, domain='pet'):
    reference: str
    name: str


class Pet(RootEntity):
    def __init__(self, name: str):
        self._reference = str(uuid.uuid4())
        self.name = name

    @classmethod
    def create(cls, name: str):
        pet = cls(name)
        pet.register_event(PetCreated(name=name, reference=pet.reference))
        return pet

    def rename(self, name: str):
        self.name = name


class IRepository(abc.ABC):
    @abc.abstractmethod
    async def save(self, entity: IRootEntity):
        ...


class IPetRepository(IRepository, abc.ABC):

    @abc.abstractmethod
    async def get(self, name: str) -> Pet:
        ...


pet_module = Module('pet')


@pet_module.register
async def create_pet(cmd: CreatePet, repository: IPetRepository):
    pet = Pet.create(cmd.name)
    await repository.save(pet)
    return pet.reference


class CreateGreetLogCommand(DomainCommand, domain='greet'):
    pet_id: str
    name: str


class SayGreetCommand(DomainCommand, domain='greet'):
    pet_id: str


class GreetReference(uuid.UUID):
    def __init__(self, value: str):
        super().__init__(value)

    @classmethod
    def generate(cls, pet_id: str) -> 'GreetReference':
        return cls(str(uuid.uuid5(NAMESPACE_URL, f'/journal/{pet_id}')))


class PerGreetJournal(RootEntity[GreetReference]):
    def __init__(self, pet_id: str, pet_name: str):
        self._reference = GreetReference.generate(pet_id)
        self.pet_name = pet_name

    def greet(self):
        return f'Hi, {self.pet_name}!'


class IPetGreetRepo(IRepository, abc.ABC):
    @abc.abstractmethod
    async def get_by_pet_id(self, pet_id: str) -> PerGreetJournal:
        ...


greet_module = Module('greet')


@greet_module.subscribe('pet.PetCreated', converter=lambda x: {"pet_id": x['reference'], "name": x['name']})
@greet_module.register
async def register_pet(cmd: CreateGreetLogCommand, repository: IPetGreetRepo):
    journal = await repository.get_by_pet_id(cmd.pet_id)
    if journal is None:
        journal = PerGreetJournal(pet_id=cmd.pet_id, pet_name=cmd.name)
        await repository.save(journal)
    return journal.reference


@greet_module.register
async def say_greet(cmd: SayGreetCommand, repository: IPetGreetRepo):
    pet = await repository.get_by_pet_id(cmd.pet_id)
    return pet.greet()


class BaseRepository(abc.ABC):
    @abc.abstractmethod
    async def _insert(self, entity: IRootEntity):
        ...

    async def save(self, entity: IRootEntity):
        await self._insert(entity)
        application = get_application()
        for event in entity.collect_events():
            await application.handle(event)


class InMemoryPetRepo(BaseRepository, IPetRepository):
    def __init__(self, memory: dict):
        self.memory = memory

    async def get(self, name: str) -> Pet:
        return self.memory.get(name)

    async def _insert(self, pet: Pet):
        self.memory[pet.name] = pet


class InMemoryGreetRepo(BaseRepository, IPetGreetRepo):
    def __init__(self, memory: dict):
        self.memory = memory

    async def get_by_pet_id(self, pet_id: str) -> PerGreetJournal:
        return self.memory.get(GreetReference.generate(pet_id))

    async def _insert(self, greet: PerGreetJournal):
        self.memory[greet.reference] = greet


# prepare app
async def main():
    app = Application(executor=AsyncExecutor())
    app.include(greet_module)
    app.include(pet_module)
    app.set_defaults('pet', repository=InMemoryPetRepo({}))
    app.set_defaults('greet', repository=InMemoryGreetRepo({}))

    # set app_globally
    set_application(app)

    fluff_id = await app.handle(CreatePet(name='Fluff'))
    max_id = await app.handle(CreatePet(name='Max'))
    greet_fluff = await app.handle(SayGreetCommand(pet_id=fluff_id))
    assert greet_fluff == 'Hi, Fluff!'

    greet_max = await app.handle(SayGreetCommand(pet_id=max_id))
    assert greet_max == 'Hi, Max!'


logging.basicConfig()
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
