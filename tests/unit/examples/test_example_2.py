import abc
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
from pyddd.domain import (
    IRootEntity,
    DomainCommand,
    DomainEvent,
    DomainName,
)
from pyddd.domain.entity import RootEntity

__pet_domain__ = DomainName("async.pet")
__greet_domain__ = DomainName("async.greet")


class CreatePet(DomainCommand, domain=__pet_domain__):
    name: str


class PetCreated(DomainEvent, domain=__pet_domain__):
    reference: str
    name: str


class Pet(RootEntity):
    name: str

    @classmethod
    def create(cls, name: str):
        pet = cls(name=name)
        pet.register_event(PetCreated(name=name, reference=str(pet.__reference__)))
        return pet

    def rename(self, name: str):
        self.name = name


class IRepository(abc.ABC):
    @abc.abstractmethod
    async def save(self, entity: IRootEntity): ...


class IPetRepository(IRepository, abc.ABC):
    @abc.abstractmethod
    async def get(self, name: str) -> Pet: ...


pet_module = Module(__pet_domain__)


@pet_module.register
async def create_pet(cmd: CreatePet, repository: IPetRepository):
    pet = Pet.create(cmd.name)
    await repository.save(pet)
    return pet.__reference__


class CreateGreetLogCommand(DomainCommand, domain=__greet_domain__):
    pet_id: str
    name: str


class SayGreetCommand(DomainCommand, domain=__greet_domain__):
    pet_id: str


class GreetReference(uuid.UUID):
    def __init__(self, value: str):
        super().__init__(value)

    @classmethod
    def generate(cls, pet_id: str) -> "GreetReference":
        return cls(str(uuid.uuid5(NAMESPACE_URL, f"/journal/{pet_id}")))


class PerGreetJournal(RootEntity[GreetReference]):
    pet_id: str
    pet_name: str

    @classmethod
    def create(cls, pet_id: str, pet_name: str) -> "PerGreetJournal":
        return cls(pet_id=pet_id, pet_name=pet_name, __reference__=GreetReference.generate(pet_id))

    def greet(self):
        return f"Hi, {self.pet_name}!"


class IPetGreetRepo(IRepository, abc.ABC):
    @abc.abstractmethod
    async def get_by_pet_id(self, pet_id: str) -> PerGreetJournal: ...


greet_module = Module(__greet_domain__)


@greet_module.subscribe(str(PetCreated.__topic__), converter=lambda x: {"pet_id": x["reference"], "name": x["name"]})
@greet_module.register
async def register_pet(cmd: CreateGreetLogCommand, repository: IPetGreetRepo):
    journal = await repository.get_by_pet_id(cmd.pet_id)
    if journal is None:
        journal = PerGreetJournal.create(pet_id=cmd.pet_id, pet_name=cmd.name)
        await repository.save(journal)
    return journal.__reference__


@greet_module.register
async def say_greet(cmd: SayGreetCommand, repository: IPetGreetRepo):
    pet = await repository.get_by_pet_id(cmd.pet_id)
    return pet.greet()


class BaseRepository(abc.ABC):
    @abc.abstractmethod
    async def _insert(self, entity: IRootEntity): ...

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
        self.memory[greet.__reference__] = greet


# prepare app
async def test():
    logging.basicConfig()
    app = Application(executor=AsyncExecutor())
    app.include(greet_module)
    app.include(pet_module)
    app.set_defaults(__pet_domain__, repository=InMemoryPetRepo({}))
    app.set_defaults(__greet_domain__, repository=InMemoryGreetRepo({}))

    # set app_globally
    set_application(app)

    await app.run_async()

    fluff_id = await app.handle(CreatePet(name="Fluff"))
    max_id = await app.handle(CreatePet(name="Max"))
    greet_fluff = await app.handle(SayGreetCommand(pet_id=str(fluff_id)))
    assert greet_fluff == "Hi, Fluff!"

    greet_max = await app.handle(SayGreetCommand(pet_id=str(max_id)))
    assert greet_max == "Hi, Max!"
