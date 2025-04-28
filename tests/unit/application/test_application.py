from unittest.mock import (
    Mock,
    AsyncMock,
)

import pytest

from pyddd.application import (
    Application,
    AsyncExecutor,
    SyncExecutor,
)
from pyddd.application import Module
from pyddd.application import (
    set_application,
    get_application,
)
from pyddd.application.abstractions import (
    IApplication,
    ApplicationSignal,
)

from pyddd.domain import (
    DomainCommand,
    DomainEvent,
)


class ExampleCommand(DomainCommand, domain="test"): ...


class ExampleEvent(DomainEvent, domain="test"): ...


class TestApplication:
    @pytest.fixture
    def application(self):
        app = Application()
        app.run()
        yield app
        app.stop()

    def test_must_implement_interface(self):
        app = Application()
        assert isinstance(app, IApplication)

    def test_include_twice(self, application):
        application.include(Module("test"))
        with pytest.raises(ValueError, match="Already registered domain 'test'"):
            application.include(Module("test"))

    def test_handle_command(self, application):
        def foo(cmd: ExampleCommand):
            return True

        module = Module("test")
        module.register(foo)
        application.include(module)
        result = application.handle(ExampleCommand())
        assert result is True

    def test_handle_event(self, application):
        def foo(cmd: ExampleCommand):
            return 1

        module = Module("test")
        event = ExampleEvent()
        module.subscribe(event.__topic__)(foo)
        application.include(module)
        result = list(application.handle(event))
        assert result == [1]

    def test_handle_unresolved_event(self, application):
        application.handle(ExampleEvent())

    def test_handle_unresolved_command(self, application):
        with pytest.raises(ValueError, match="Unregistered module for domain"):
            application.handle(ExampleCommand())

    def test_handle_with_defaults(self, application):
        def foo(cmd: ExampleCommand, atr: str):
            return atr

        application.set_defaults("test", atr="success")
        module = Module("test")
        module.register(foo)
        application.include(module)
        result = application.handle(ExampleCommand())
        assert result == "success"

    def test_handle_with_overwrite_defaults(self, application):
        def foo(cmd: ExampleCommand, atr: str):
            return atr

        application.set_defaults("test", atr="fail")
        module = Module("test")
        module.register(foo)
        application.include(module)
        result = application.handle(ExampleCommand(), atr="success")
        assert result == "success"

    def test_must_return_exceptions_when_handle_event(self, application):
        module = Module(domain="test")

        @module.subscribe(ExampleEvent.__topic__)
        def foo(command: ExampleCommand):
            raise Exception()

        @module.subscribe(ExampleEvent.__topic__)
        def bzz(command: ExampleCommand):
            return True

        application.include(module)
        result = list(application.handle(ExampleEvent()))
        assert isinstance(result[0], Exception)
        assert result[1] is True

    def test_handle_unknown_message_type(self, application):
        with pytest.raises(RuntimeError):
            application.handle(...)

    def test_app_must_run(self):
        app = Application()
        app.run()
        assert app.is_running is True

    async def test_app_must_arun(self):
        app = Application()
        await app.run_async()
        assert app.is_running is True

    def test_app_must_stop(self):
        app = Application()
        app.run()
        app.stop()
        assert app.is_stopped is True

    async def test_app_must_astop(self):
        app = Application()
        await app.run_async()
        await app.stop_async()
        assert app.is_stopped is True

    def test_app_must_not_be_running_by_default(self):
        app = Application()
        assert app.is_running is False

    def test_app_must_not_be_stopping_by_default(self):
        app = Application()
        assert app.is_stopped is False

    def test_app_could_run_and_stop(self):
        app = Application()
        app.run()
        app.stop()
        assert app.is_running is False

    def test_can_not_stop_before_run(self):
        app = Application()
        with pytest.raises(RuntimeError, match="Can not stop not running application"):
            app.stop()

    async def test_can_not_astop_before_run(self):
        app = Application()
        with pytest.raises(RuntimeError, match="Can not stop not running application"):
            await app.stop_async()

    def test_can_not_run_after_stop(self):
        app = Application()
        app.run()
        app.stop()
        with pytest.raises(RuntimeError):
            app.run()

    async def test_can_not_arun_after_astop(self):
        app = Application()
        await app.run_async()
        await app.stop_async()
        with pytest.raises(RuntimeError):
            await app.run_async()

    def test_must_call_before_run_and_after_run_if_run(self):
        app = Application()
        mock = Mock()
        app.subscribe(ApplicationSignal.BEFORE_RUN, mock)
        app.subscribe(ApplicationSignal.AFTER_RUN, mock)
        app.run()
        assert mock.call_count == 2

    async def test_must_call_before_run_and_after_run_if_arun(self):
        app = Application()
        mock = AsyncMock()
        app.subscribe(ApplicationSignal.BEFORE_RUN, mock)
        app.subscribe(ApplicationSignal.AFTER_RUN, mock)
        await app.run_async()
        assert mock.call_count == 2

    def test_must_run_before_stop_and_after_stop_if_stop(self):
        app = Application()
        mock = Mock()
        app.subscribe(ApplicationSignal.BEFORE_STOP, mock)
        app.subscribe(ApplicationSignal.AFTER_STOP, mock)
        app.run()
        app.stop()
        assert mock.call_count == 2

    async def test_must_run_before_stop_and_after_stop_if_stop_async(self):
        app = Application()
        mock = AsyncMock()
        app.subscribe(ApplicationSignal.BEFORE_STOP, mock)
        app.subscribe(ApplicationSignal.AFTER_STOP, mock)
        await app.run_async()
        await app.stop_async()
        assert mock.call_count == 2

    def test_can_not_handle_not_running_error(self):
        app = Application()
        with pytest.raises(RuntimeError, match="Can not handle test.ExampleEvent. App is not running!"):
            app.handle(ExampleEvent())

    async def test_must_set_async_executor_if_run_async(self):
        app = Application()
        await app.run_async()
        assert isinstance(app._executor, AsyncExecutor)

    def test_must_set_sync_executor_if_run(self):
        app = Application()
        app.run()
        assert isinstance(app._executor, SyncExecutor)


def test_set_and_get_application():
    app = Application()
    set_application(app)
    assert get_application() == app
