import pytest

from .cloud_tasks import example_task


def test_example_task():
    # breakpoint()
    response = example_task(payload=1).execute()
    print(response)
    assert 1 == 0
