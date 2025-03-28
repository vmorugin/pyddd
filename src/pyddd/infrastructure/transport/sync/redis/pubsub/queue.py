import threading
import time
import json
import logging
import uuid
from concurrent.futures import (
    ThreadPoolExecutor,
)

from redis.client import PubSub

from pyddd.infrastructure.transport.sync.domain.abstractions import (
    INotificationQueue,
    ICallback,
)
from pyddd.infrastructure.transport.sync.domain import Notification


class PubSubNotificationQueue(INotificationQueue):
    def __init__(self, pubsub: PubSub, logger_name: str = 'notification.queue'):
        self._pubsub = pubsub
        self._running = False
        self._executor = ThreadPoolExecutor()
        self._logger = logging.getLogger(logger_name)

    def bind(self, topic: str):
        self._pubsub.subscribe(topic)

    def consume(self, callback: ICallback):
        self._running = True
        self._executor.submit(self._long_pull, callback)

    def stop_consume(self):
        self._running = False
        self._pubsub.unsubscribe()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _long_pull(self, callback: ICallback):
        while self._running:
            try:
                for message in self._pubsub.listen():
                    if message['type'] == 'message':
                        notification = Notification(
                            message_id=str(uuid.uuid4()),
                            name=message['channel'].decode(),
                            payload=json.loads(message['data']),
                        )
                        threading.Thread(target=callback, args=(notification,), daemon=True).start()
            except Exception as exc:
                self._logger.error("Unexpected error while pulling pubsub", exc_info=exc)
            time.sleep(0.001)
