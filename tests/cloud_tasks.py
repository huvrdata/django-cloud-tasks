from django_cloud_tasks.decorators import task


@task(queue="default")
def example_task(payload):
    print(payload)
