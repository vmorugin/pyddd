import datetime as dt

from pyddd.domain.message import (
    Message,
)
from pyddd.domain.abstractions import (
    MessageType,
)


class TestMessage:
    def test_message(self):
        message = Message(
            full_name="users.sub.UserCreated",
            message_type=MessageType.EVENT,
            message_id="123",
            payload=dict(reference="123"),
        )
        assert message.__type__ == "EVENT"
        assert message.__message_name__ == "UserCreated"
        assert message.__domain__ == "users.sub"
        assert message.__version__ == 1
        assert message.to_dict() == {"reference": "123"}
        assert message.to_json() == '{"reference": "123"}'
        assert isinstance(message.__timestamp__, dt.datetime)

    def test_eq(self):
        message = Message(
            full_name="users.sub.UserCreated",
            message_type=MessageType.EVENT,
            message_id="123",
            payload=dict(reference="123"),
        )
        assert message == message
