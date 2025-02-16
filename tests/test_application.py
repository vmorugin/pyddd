import pytest

from pyddd.application import Application
from pyddd.application import Module
from pyddd.application import (
    set_application,
    get_application,
)
from pyddd.application.abstractions import IApplication

from pyddd.domain import (
    DomainCommand,
    DomainEvent,
)


class ExampleCommand(DomainCommand, domain='test'):
    ...


class ExampleEvent(DomainEvent, domain='test'):
    ...


class TestApplication:
    def test_must_implement_interface(self):
        app = Application()
        assert isinstance(app, IApplication)

    def test_include_twice(self):
        app = Application()
        app.include(Module('test'))
        with pytest.raises(ValueError, match="Already registered domain 'test'"):
            app.include(Module('test'))

    def test_handle_command(self):
        def foo(cmd: ExampleCommand):
            return True

        app = Application()
        module = Module('test')
        module.register(foo)
        app.include(module)
        result = app.handle(ExampleCommand())
        assert result is True

    def test_handle_event(self):
        def foo(cmd: ExampleCommand):
            return 1

        app = Application()
        module = Module('test')
        event = ExampleEvent()
        module.subscribe(event.topic)(foo)
        app.include(module)
        result = list(app.handle(event))
        assert result == [1]

    def test_handle_unresolved_event(self):
        app = Application()
        app.handle(ExampleEvent())

    def test_handle_unresolved_command(self):
        app = Application()
        with pytest.raises(ValueError, match='Unregistered module for domain'):
            app.handle(ExampleCommand())

    def test_handle_with_defaults(self):
        def foo(cmd: ExampleCommand, atr: str):
            return atr

        app = Application()
        app.set_defaults('test', atr='success')
        module = Module('test')
        module.register(foo)
        app.include(module)
        result = app.handle(ExampleCommand())
        assert result == 'success'

    def test_handle_with_overwrite_defaults(self):
        def foo(cmd: ExampleCommand, atr: str):
            return atr

        app = Application()
        app.set_defaults('test', atr='fail')
        module = Module('test')
        module.register(foo)
        app.include(module)
        result = app.handle(ExampleCommand(), atr='success')
        assert result == 'success'

    def test_must_return_exceptions_when_handle_event(self):
        module = Module(domain='test')

        @module.subscribe(ExampleEvent.__topic__)
        def foo(command: ExampleCommand):
            raise Exception()

        @module.subscribe(ExampleEvent.__topic__)
        def bzz(command: ExampleCommand):
            return True

        application = Application()
        application.include(module)
        result = list(application.handle(ExampleEvent()))
        assert isinstance(result[0], Exception)
        assert result[1] is True

    def test_handle_unknown_message_type(self):
        app = Application()
        with pytest.raises(RuntimeError):
            app.handle(...)

    def test_app_must_run(self):
        app = Application()
        app.run()
        assert app.is_running is True


def test_set_and_get_application():
    app = Application()
    set_application(app)
    assert get_application() == app
