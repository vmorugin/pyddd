from pyddd.infrastructure.transport.sync.domain.abstractions import (
    INotification,
    AskProtocol,
    RejectProtocol,
)


def _mock_ask(*args, **kwargs):
    return


class Notification(INotification):
    def __init__(
            self,
            message_id: str,
            name: str,
            payload: dict,
            ask_func: AskProtocol = _mock_ask,
            reject_func: RejectProtocol = _mock_ask,
    ):
        self._reference = message_id
        self._name = name
        self._payload = payload
        self._ask_func = ask_func
        self._reject_func = reject_func

    @property
    def message_id(self) -> str:
        return self._reference

    @property
    def name(self) -> str:
        return self._name

    @property
    def payload(self) -> dict:
        return self._payload

    def ack(self) -> None:
        return self._ask_func()

    def reject(self, requeue: bool) -> None:
        return self._reject_func(requeue)
