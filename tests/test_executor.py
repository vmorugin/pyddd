from unittest.mock import Mock

from pyddd.application.executor import (
    AsyncExecutor,
    SyncExecutor,
)
from pyddd.application.abstractions import IExecutor
from pyddd.domain import (
    DomainCommand,
    DomainEvent,
)


class ExampleCommand(DomainCommand, domain='test'):
    ...


class TestEvent(DomainEvent, domain='test'):
    ...


class TestSyncExecutor:
    def test_init(self):
        executor = SyncExecutor()
        assert isinstance(executor, IExecutor)

    def test_process_handler(self):
        def foo(value: str):
            return value

        executor = SyncExecutor()
        result = executor.process_handler(handler=foo, value='123')
        assert result is '123'

    def test_process_event(self):
        def foo(callback):
            callback(True)

        executor = SyncExecutor()
        mock = Mock()
        executor.process_handlers(handlers=[foo], callback=mock)
        mock.assert_called_with(True)

    def test_process_event_must_return_results(self):
        def foo():
            return 1

        def bar():
            return 2

        executor = SyncExecutor()
        result = executor.process_handlers(handlers=[foo, bar])
        assert result == [1, 2]

    def test_must_execute_events_with_errors(self):
        def foo():
            raise RuntimeError()

        def bar():
            return 2

        executor = SyncExecutor()
        result = executor.process_handlers(handlers=[foo, bar])
        assert isinstance(result[0], RuntimeError)
        assert result[1] == 2


class TestAsyncExecutor:
    def test_init(self):
        executor = AsyncExecutor()
        assert isinstance(executor, IExecutor)

    async def test_process_command(self):
        async def foo():
            return True

        executor = AsyncExecutor()
        result = await executor.process_handler(handler=foo)
        assert result is True

    async def test_process_event(self):
        async def foo(callback):
            callback(True)

        executor = AsyncExecutor()
        mock = Mock()
        await executor.process_handlers(handlers=[foo], callback=mock)
        mock.assert_called_with(True)

    async def test_process_event_must_return_results(self):
        async def foo():
            return 1

        async def bar():
            return 2

        executor = AsyncExecutor()
        result = await executor.process_handlers(handlers=[foo, bar])
        assert result == [1, 2]

    async def test_must_execute_events_with_errors(self):
        async def foo():
            raise RuntimeError()

        async def bar():
            return 2

        executor = AsyncExecutor()
        result = await executor.process_handlers(handlers=[foo, bar])
        assert isinstance(result[0], RuntimeError)
        assert result[1] == 2
