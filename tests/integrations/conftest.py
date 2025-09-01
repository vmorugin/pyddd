import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import AsyncRedisContainer


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:14.5", driver=None) as postgres:
        yield {
            "host": postgres.get_container_host_ip(),
            "port": postgres.get_exposed_port(postgres.port),
            "dbname": postgres.dbname,
            "username": postgres.username,
            "password": postgres.password,
        }


@pytest.fixture(scope="session")
def redis_container():
    with AsyncRedisContainer("redis:6.2.10") as redis:
        yield redis
