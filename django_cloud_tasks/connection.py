import hashlib
import os.path
import tempfile


from google.cloud import tasks_v2

from .apps import DCTConfig


class cached_property(object):
    def __init__(self, fget):
        self.fget = fget
        self.func_name = fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return None
        value = self.fget(obj)
        setattr(obj, self.func_name, value)
        return value


class GoogleCloudClient(object):
    @cached_property
    def client(self):
        client = tasks_v2.CloudTasksClient(
            credentials=DCTConfig.google_cloud_credentials()
        )
        return client

    @cached_property
    def tasks_endpoint(self):
        client = self.client
        tasks_endpoint = client.projects().locations().queues().tasks()
        return tasks_endpoint


connection = GoogleCloudClient()
