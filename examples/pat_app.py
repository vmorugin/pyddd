import abc
import dataclasses
import uuid
from uuid import NAMESPACE_URL

from application import (
    Module,
    Application,
)
from application.application import (
    get_application,
    set_application,
)
from domain import (
    RootEntity,
    DomainCommand,
    DomainEvent,
    EntityId,
)


class CreatePat(DomainCommand, domain='pet'):
    name: str


class PatCreated(DomainEvent, domain='pet'):
    pat_id: str
    name: str


@dataclasses.dataclass(kw_only=True)
class Pet(RootEntity):
    def __init__(self, name: str):
        super().__init__(__reference__=str(uuid.uuid4()))
        self.name = name

    @classmethod
    def create(cls, name: str):
        pat = cls(name)
        pat.register_event(PatCreated(name=name, pat_id=pat.__reference__))
        return pat

    def rename(self, name: str):
        self.name = name


class IRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, entity: RootEntity):
        ...


class IPetRepository(IRepository, abc.ABC):

    @abc.abstractmethod
    def get(self, name: str) -> Pet:
        ...


pat_module = Module('pet')


@pat_module.register
def create_pat(cmd: CreatePat, repository: IPetRepository):
    pat = Pet.create(cmd.name)
    repository.save(pat)
    return pat.__reference__


class InsertGreetLogCommand(DomainCommand, domain='greet'):
    pat_id: str
    name: str


class SayGreetCommand(DomainCommand, domain='greet'):
    pat_id: str


class GreetReference(EntityId):
    def __init__(self, value: uuid.UUID):
        self._value = value

    @classmethod
    def generate(cls, pat_id: str) -> 'EntityId':
        return cls(uuid.uuid5(NAMESPACE_URL, f'/journal/{pat_id}'))

    def __hash__(self):
        return hash(self._value)


@dataclasses.dataclass
class PerGreetJournal(RootEntity):
    def __init__(self, pat_id: str, pat_name: str):
        super().__init__(__reference__=GreetReference.generate(pat_id))
        self.pat_name = pat_name

    def greet(self):
        return f'Hi, {self.pat_name}!'


class IPetGreetRepo(IRepository, abc.ABC):
    @abc.abstractmethod
    def get_by_pat_id(self, pat_id: str) -> PerGreetJournal:
        ...


greet_module = Module('greet')


@greet_module.subscribe('pet.PatCreated')
@greet_module.register
def register_pat(cmd: InsertGreetLogCommand, repository: IPetGreetRepo):
    journal = repository.get_by_pat_id(cmd.pat_id)
    if journal is None:
        journal = PerGreetJournal(pat_id=cmd.pat_id, pat_name=cmd.name)
        repository.save(journal)
    return journal.__reference__


@greet_module.register
def say_greet(cmd: SayGreetCommand, repository: IPetGreetRepo):
    pat = repository.get_by_pat_id(cmd.pat_id)
    return pat.greet()


class BaseRepository(abc.ABC):
    @abc.abstractmethod
    def _insert(self, entity: RootEntity):
        ...

    def save(self, entity: RootEntity):
        self._insert(entity)
        application = get_application()
        for event in entity.collect_events():
            application.handle(event)


class InMemoryPetRepo(BaseRepository, IPetRepository):
    def __init__(self, memory: dict):
        self.memory = memory

    def get(self, name: str) -> Pet:
        return self.memory.get(name)

    def _insert(self, pat: Pet):
        self.memory[pat.name] = pat


class InMemoryGreetRepo(BaseRepository, IPetGreetRepo):
    def __init__(self, memory: dict):
        self.memory = memory

    def get_by_pat_id(self, pat_id: str) -> PerGreetJournal:
        return self.memory.get(GreetReference.generate(pat_id))

    def _insert(self, greet: PerGreetJournal):
        self.memory[greet.__reference__] = greet


# prepare app
app = Application()
app.include(greet_module)
app.include(pat_module)
app.set_defaults('pet', repository=InMemoryPetRepo({}))
app.set_defaults('greet', repository=InMemoryGreetRepo({}))

# set app_globally
set_application(app)

fluff_id = app.handle(CreatePat(name='Fluff'))
max_id = app.handle(CreatePat(name='Max'))
greet_fluff = app.handle(SayGreetCommand(pat_id=fluff_id))
assert greet_fluff == 'Hi, Fluff!'

greet_max = app.handle(SayGreetCommand(pat_id=max_id))
assert greet_max == 'Hi, Max!'