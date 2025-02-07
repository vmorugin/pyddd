import time
import datetime as dt
from unittest.mock import Mock

from application import (
    SyncExecutor,
    CommandHandler,
    EventHandler,
)
from application.executor import IExecutor
from domain import (
    DomainCommand,
    DomainEvent,
)


class TestCommand(DomainCommand, domain='test'):
    ...


class TestEvent(DomainEvent, domain='test'):
    ...


class TestSyncExecutor:
    def test_init(self):
        executor = SyncExecutor()
        assert isinstance(executor, IExecutor)

    def test_process_command(self):
        def foo(cmd: TestCommand):
            return True

        executor = SyncExecutor()
        result = executor.process_command(command=TestCommand(), handler=CommandHandler(foo))
        assert result is True

    def test_process_event(self):
        def foo(cmd: TestCommand, callback):
            callback(True)

        executor = SyncExecutor()
        mock = Mock()
        executor.process_event(event=TestEvent(), handlers=[EventHandler(CommandHandler(foo))], callback=mock)
        mock.assert_called_with(True)

    def test_process_event_must_return_results(self):
        def foo(cmd: TestCommand):
            return 1

        def bar(cmd: TestCommand):
            return 2

        executor = SyncExecutor()
        result = executor.process_event(
            event=TestEvent(),
            handlers=[
                EventHandler(CommandHandler(foo)),
                EventHandler(CommandHandler(bar))
            ]
        )
        assert result == [1, 2]

    def test_must_execute_events_with_errors(self):
        def foo(cmd: TestCommand):
            raise RuntimeError()

        def bar(cmd: TestCommand):
            return 2

        executor = SyncExecutor()
        result = executor.process_event(
            event=TestEvent(),
            handlers=[
                EventHandler(CommandHandler(foo)),
                EventHandler(CommandHandler(bar))
            ]
        )
        assert isinstance(result[0], RuntimeError)
        assert result[1] == 2