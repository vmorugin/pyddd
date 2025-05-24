import logging
import threading
import time

from pyddd.infrastructure.transport.sync.domain.abstractions import (
    INotificationQueue,
    IMessageHandler,
    ICallback,
)


class NotificationQueue(INotificationQueue):
    def __init__(
        self,
        message_handler: IMessageHandler,
        *,
        batch_size: int = 50,
        delay_ms: int = 10,
        logger_name: str = "pyddd.transport.queue",
    ):
        self._handler = message_handler
        self._topics: set[str] = set()
        self._batch_size = batch_size
        self._delay_ms = delay_ms * 0.001
        self._logger = logging.getLogger(logger_name)
        self._is_running = False
        self._threads: list[threading.Thread] = []

    def bind(self, topic: str):
        self._topics.add(topic)
        self._handler.bind(topic)

    def consume(self, callback: ICallback):
        self._is_running = True
        for topic in self._topics:
            thread = threading.Thread(
                target=self._long_pull,
                args=(
                    topic,
                    callback,
                ),
                daemon=True,
            )
            self._threads.append(thread)
            thread.start()

    def stop_consume(self):
        self._is_running = False
        for thread in self._threads:
            thread.join(self._delay_ms)

    def _long_pull(self, topic: str, callback: ICallback):
        while self._is_running:
            try:
                messages = self._handler.read(topic, limit=self._batch_size)
                for message in messages:
                    thread = threading.Thread(
                        target=self._process_callback,
                        args=(callback, message),
                        daemon=True,
                    )
                    self._threads.append(thread)
                    thread.start()
            except Exception as exc:
                self._logger.error(f"Unexpected error while pulling {topic} messages!", exc_info=exc)
            time.sleep(self._delay_ms)

    def _process_callback(self, callback, message):
        try:
            callback(message)
        except Exception as exc:
            self._logger.info("Callback processing error", exc_info=exc)
