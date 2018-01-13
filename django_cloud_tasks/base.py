import base64
import json
import logging
import time

from django.conf import settings

from .apps import DCTConfig
from .connection import connection

logger = logging.getLogger(__name__)


def retry(retry_limit, retry_interval):
    """
    Decorator for retrying task scheduling
    """

    def decorator(f):
        def wrapper():
            attempts_left = retry_limit
            error = None
            while attempts_left > 1:
                try:
                    return f()
                except Exception as e:
                    error = e
                    msg = 'Task scheduling failed. Reason: {0}. Retrying...'.format(str(e))
                    logger.warning(msg)
                    time.sleep(retry_interval)
                    attempts_left -= 1

            # Limit exhausted
            error.args = ('Task scheduling limit exhausted',) + error.args
            raise error

        return wrapper

    return decorator


def batch_callback_logger(id, message, exception):
    if exception:
        resp, _bytes = exception.args
        decoded = json.loads(_bytes.decode('utf-8'))
        raise Exception(decoded['error']['message'])


def batch_execute(tasks, retry_limit=30, retry_interval=3):
    """
    Executes tasks in batch
    :param tasks: list of CloudTaskWrapper objects
    :param retry_limit: How many times task scheduling will be attempted
    :param retry_interval: Interval between task scheduling attempts in seconds
    """
    if len(tasks) >= 1000:
        raise Exception('Maximum number of tasks in batch cannot exceed 1000')
    client = connection.client
    batch = client.new_batch_http_request()
    for t in tasks:
        batch.add(t.create_cloud_task(), callback=batch_callback_logger)

    if not retry_limit:
        return batch.execute()
    else:
        return retry(retry_limit=retry_limit, retry_interval=retry_interval)(batch.execute)()


class BaseTask(object):
    pass


class CloudTaskWrapper(object):
    def __init__(self, base_task, queue, data):
        self._base_task = base_task
        self._data = data
        self._queue = queue
        self._connection = None
        self.setup()

    def setup(self):
        if not connection.client:
            con = connection.configure(**settings.DJANGO_CLOUD_TASKS)
        else:
            con = connection
        self._connection = con

    def execute(self, retry_limit=10, retry_interval=5):
        """
        Enqueue cloud task and send for execution
        :param retry_limit: How many times task scheduling will be attempted
        :param retry_interval: Interval between task scheduling attempts in seconds
        """
        if not retry_limit:
            return self.create_cloud_task().execute()
        else:
            return retry(retry_limit=retry_limit, retry_interval=retry_interval)(self.create_cloud_task().execute)()

    def run(self):
        """
        Runs actual task function
        """
        return self._base_task.run(**self._data) if self._data else self._base_task.run()

    def set_queue(self, queue):
        self._queue = queue

    @property
    def _cloud_task_queue_name(self):
        return '{}/queues/{}'.format(DCTConfig.project_location_name(), self._queue)

    def create_cloud_task(self):
        body = {
            'task': {
                'appEngineHttpRequest': {
                    'httpMethod': 'POST',
                    'relativeUrl': DCTConfig.task_handler_root_url()
                }
            }
        }

        payload = {
            'internal_task_name': self._base_task.internal_task_name,
            'data': self._data
        }
        payload = json.dumps(payload)

        base64_encoded_payload = base64.b64encode(payload.encode())
        converted_payload = base64_encoded_payload.decode()

        body['task']['appEngineHttpRequest']['payload'] = converted_payload

        task = self._connection.tasks_endpoint.create(parent=self._cloud_task_queue_name, body=body)

        return task
