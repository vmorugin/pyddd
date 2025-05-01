import abc
import typing as t
import uuid
from copy import deepcopy
from enum import Enum

from pyddd.application import (
    Application,
    Module,
)
from pyddd.domain import DomainCommand
from pyddd.domain.entity import RootEntity
from pyddd.domain.types import DomainName

from pyddd.infrastructure.persistence.abstractions import (
    IUnitOfWorkBuilder,
    IRepository,
    IRepositoryBuilder,
    IUnitOfWorkCtxMgr,
    TRepo,
    TLock,
)
from pyddd.infrastructure.persistence.uow import UnitOfWorkBuilder

__domain__ = DomainName('workspace')

module = Module(__domain__)


class BaseCommand(DomainCommand, domain=__domain__):
    pass


class CreateWorkspace(BaseCommand):
    tenant_name: str
    project_name: str


class DeleteWorkspace(BaseCommand):
    workspace_id: str


class WorkspaceId(str):
    ...


class TenantId(str):
    ...


class ProjectId(str):
    ...


class WorkspaceStatus(str, Enum):
    CREATED = 'CREATED'
    DELETED = 'DELETED'


class Tenant(RootEntity[TenantId]):
    name: str


class Project(RootEntity[ProjectId]):
    name: str
    tenant_id: TenantId

    class Config:
        arbitrary_types_allowed = True


class Workspace(RootEntity[WorkspaceId]):
    tenant: Tenant
    project: Project
    status: WorkspaceStatus

    class Config:
        arbitrary_types_allowed = True

    def delete(self):
        self.status = WorkspaceStatus.DELETED


class ITenantRepository(abc.ABC):
    @abc.abstractmethod
    def create(self, name: str) -> Tenant:
        ...


class IProjectRepository(abc.ABC):
    @abc.abstractmethod
    def create(self, name: str, tenant_id: TenantId) -> Project:
        ...


class IWorkspaceRepository(abc.ABC):
    @abc.abstractmethod
    def create(self, tenant: Tenant, project: Project) -> Workspace:
        ...

    @abc.abstractmethod
    def get(self, reference: WorkspaceId) -> Workspace:
        ...


class IWorkspaceRepoFactory(IRepository, abc.ABC):
    @abc.abstractmethod
    def tenant(self) -> ITenantRepository:
        ...

    @abc.abstractmethod
    def workspace(self) -> IWorkspaceRepository:
        ...

    @abc.abstractmethod
    def project(self) -> IProjectRepository:
        ...


@module.register
async def create_workspace_and_tenant_and_project(
        cmd: CreateWorkspace,
        uow_builder: IUnitOfWorkBuilder[IWorkspaceRepoFactory]
        ) -> WorkspaceId:
    """
    This is an example of UoW with multi-repository. Not recommend to do the same in production!
    Right way - separate the usecase to 3:
    create_tenant, create_project, create_workspace.
    """
    with uow_builder() as uow:
        tenant_repo = uow.repository.tenant()
        project_repo = uow.repository.project()
        workspace_repo = uow.repository.workspace()
        tenant = tenant_repo.create(name=cmd.tenant_name)
        project = project_repo.create(name=cmd.project_name, tenant_id=tenant.__reference__)
        workspace = workspace_repo.create(tenant=tenant, project=project)
        uow.apply()
    return workspace.__reference__


@module.register
async def delete_workspace(cmd: DeleteWorkspace, uow_builder: IUnitOfWorkBuilder[IWorkspaceRepoFactory]):
    with uow_builder() as uow:
        workspace_repo = uow.repository.workspace()
        workspace = workspace_repo.get(reference=WorkspaceId(cmd.workspace_id))
        workspace.delete()
        uow.apply()


class BaseInMemoryRepo:
    def __init__(self):
        self._seen = {}

    def save(self, mem: dict):
        for ref, agg in self._seen.items():
            mem[ref] = agg
        self._seen.clear()


class InMemoryTenantRepo(ITenantRepository, BaseInMemoryRepo):

    def create(self, name: str) -> Tenant:
        tenant = Tenant(name=name, __reference__=TenantId(str(uuid.uuid4())))
        self._seen[tenant.__reference__] = tenant
        return tenant


class InMemoryProjectRepo(IProjectRepository, BaseInMemoryRepo):

    def create(self, name: str, tenant_id: TenantId) -> Project:
        project = Project(name=name, tenant_id=tenant_id, __reference__=ProjectId(str(uuid.uuid4())))
        self._seen[project.__reference__] = project
        return project


class InMemoryWorkspaceRepo(IWorkspaceRepository, BaseInMemoryRepo):
    def __init__(self, memory: dict):
        super().__init__()
        self._memory = memory

    def create(self, tenant: Tenant, project: Project) -> Workspace:
        workspace = Workspace(
            __reference__=WorkspaceId(str(uuid.uuid4())),
            tenant=tenant,
            project=project,
            status=WorkspaceStatus.CREATED
        )
        self._seen[workspace.__reference__] = workspace
        return workspace

    def get(self, reference: WorkspaceId) -> Workspace:
        return self._memory[reference]


class RepositoryFactory(IWorkspaceRepoFactory):
    def __init__(
            self,
            memory: dict,
            tenant_repo: InMemoryTenantRepo,
            project_repo: InMemoryProjectRepo,
            workspace_repo: InMemoryWorkspaceRepo,
    ):
        self._memory = memory
        self._tenant_repo = tenant_repo
        self._project_repo = project_repo
        self._workspace_repo = workspace_repo

    def tenant(self) -> ITenantRepository:
        return self._tenant_repo

    def workspace(self) -> IWorkspaceRepository:
        return self._workspace_repo

    def project(self) -> IProjectRepository:
        return self._project_repo

    def commit(self):
        # txn emulation
        rollback_mem = deepcopy(self._memory)

        self._tenant_repo.save(rollback_mem)
        self._project_repo.save(rollback_mem)
        self._workspace_repo.save(rollback_mem)

        # only save if all repos success apply changes.
        self._memory.update(rollback_mem)


class RepoBuilder(IRepositoryBuilder):
    def __init__(
            self,
            memory: dict,
            tenant_repo: InMemoryTenantRepo,
            project_repo: InMemoryProjectRepo,
            workspace_repo: InMemoryWorkspaceRepo,
    ):
        self._memory = memory
        self._tenant_repo = tenant_repo
        self._project_repo = project_repo
        self._workspace_repo = workspace_repo

    def __call__(self, __uow_context_manager: IUnitOfWorkCtxMgr[TRepo, TLock]) -> TRepo | t.Awaitable[TRepo]:
        return RepositoryFactory(
            memory=self._memory,
            tenant_repo=self._tenant_repo,
            project_repo=self._project_repo,
            workspace_repo=self._workspace_repo
        )


async def test_create_workspace_example():
    """
    This is an example how we can use UoW with multiple repositories.
    V. Vernon does not recommend saving multiple aggregates in one transaction.
    """
    app = Application()
    database = {}
    tenant_repo = InMemoryTenantRepo()
    project_repo = InMemoryProjectRepo()
    workspace_repo = InMemoryWorkspaceRepo(database)
    module.set_defaults(
        dict(
            uow_builder=UnitOfWorkBuilder(
                repository_builder=RepoBuilder(
                    memory=database,
                    tenant_repo=tenant_repo,
                    project_repo=project_repo,
                    workspace_repo=workspace_repo
                )
            )

        )
    )
    app.include(module)

    await app.run_async()

    workspace_id = await app.handle(CreateWorkspace(tenant_name='default', project_name='pyddd'))

    workspace = workspace_repo.get(workspace_id)
    assert isinstance(workspace, Workspace)
    assert workspace.status == WorkspaceStatus.CREATED
    assert workspace.project.name == 'pyddd'
    assert workspace.tenant.name == 'default'

    await app.handle(DeleteWorkspace(workspace_id=workspace_id))

    workspace = workspace_repo.get(workspace_id)
    assert workspace.status == WorkspaceStatus.DELETED
