import abc
import logging
import time
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
from pyddd.domain import (
    IRootEntity,
    DomainCommand,
    DomainEvent,
)
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

    def rename(self, name: str):
        self.name = name


class IRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, entity: IRootEntity): ...


class IPetRepository(IRepository, abc.ABC):
    @abc.abstractmethod
    def get(self, name: str) -> Pet: ...


pet_module = Module("pet")


@pet_module.register
def create_pet(cmd: CreatePet, repository: IPetRepository):
    pet = Pet.create(cmd.name)
    repository.save(pet)
    return pet.__reference__


class InsertGreetLogCommand(DomainCommand, domain="greet"):
    pet_id: str
    name: str


class SayGreetCommand(DomainCommand, domain="greet"):
    pet_id: str


class GreetReference(uuid.UUID):
    def __init__(self, value: uuid.UUID):
        super().__init__(str(value))

    @classmethod
    def generate(cls, pet_id: str) -> "GreetReference":
        return cls(uuid.uuid5(NAMESPACE_URL, f"/journal/{pet_id}"))


class PerGreetJournal(RootEntity[GreetReference]):
    pet_id: str
    pet_name: str

    @classmethod
    def create(cls, pet_id: str, pet_name: str) -> "PerGreetJournal":
        journal = PerGreetJournal(pet_id=pet_id, pet_name=pet_name, __reference__=GreetReference.generate(pet_id))
        return journal

    def greet(self):
        return f"Hi, {self.pet_name}!"


class IPetGreetRepo(IRepository, abc.ABC):
    @abc.abstractmethod
    def get_by_pet_id(self, pet_id: str) -> PerGreetJournal: ...


greet_module = Module("greet")


@greet_module.subscribe("pet.PetCreated")
@greet_module.register
def register_pet(cmd: InsertGreetLogCommand, repository: IPetGreetRepo):
    journal = repository.get_by_pet_id(cmd.pet_id)
    if journal is None:
        journal = PerGreetJournal.create(pet_id=cmd.pet_id, pet_name=cmd.name)
        repository.save(journal)
    return journal.__reference__


@greet_module.register
def say_greet(cmd: SayGreetCommand, repository: IPetGreetRepo):
    pet = repository.get_by_pet_id(cmd.pet_id)
    return pet.greet()


class BaseRepository(abc.ABC):
    @abc.abstractmethod
    def _insert(self, entity: IRootEntity): ...

    def save(self, entity: IRootEntity):
        self._insert(entity)
        application = get_application()
        for event in entity.collect_events():
            application.handle(event)


class InMemoryPetRepo(BaseRepository, IPetRepository):
    def __init__(self, memory: dict):
        self.memory = memory

    def get(self, name: str) -> Pet:
        return self.memory.get(name)

    def _insert(self, pet: Pet):
        self.memory[pet.name] = pet


class InMemoryGreetRepo(BaseRepository, IPetGreetRepo):
    def __init__(self, memory: dict):
        self.memory: dict[GreetReference, PerGreetJournal] = memory

    def get_by_pet_id(self, pet_id: str) -> PerGreetJournal:
        return self.memory.get(GreetReference.generate(pet_id))

    def _insert(self, greet: PerGreetJournal):
        self.memory[greet.__reference__] = greet


def test():
    logging.basicConfig()

    # prepare app
    app = Application()
    app.include(greet_module)
    app.include(pet_module)
    app.set_defaults("pet", repository=InMemoryPetRepo({}))
    app.set_defaults("greet", repository=InMemoryGreetRepo({}))

    # set app_globally
    set_application(app)

    app.run()

    fluff_id = app.handle(CreatePet(name="Fluff"))
    max_id = app.handle(CreatePet(name="Max"))

    # wait till event executed
    time.sleep(0.01)

    greet_fluff = app.handle(SayGreetCommand(pet_id=str(fluff_id)))
    assert greet_fluff == "Hi, Fluff!"

    greet_max = app.handle(SayGreetCommand(pet_id=str(max_id)))
    assert greet_max == "Hi, Max!"
