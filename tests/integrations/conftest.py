import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:14.5") as postgres:
        yield {
            "host": postgres.get_container_host_ip(),
            "port": postgres.get_exposed_port(postgres.port),
            "dbname": postgres.dbname,
            "username": postgres.username,
            "password": postgres.password,
        }


@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:6.2.10") as redis:
        yield {
            "host": redis.get_container_host_ip(),
            "port": redis.get_exposed_port(redis.port),
        }
