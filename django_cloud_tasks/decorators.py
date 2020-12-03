from functools import partial, wraps

# from .base import BaseTask, CloudTaskWrapper
from .registries import registry


def _gen_internal_task_name(task_func):
    internal_task_name = ".".join((task_func.__module__, task_func.__name__))
    return internal_task_name


def create_task(task_class, func, **kwargs):
    run = partial(func)

    internal_task_name = _gen_internal_task_name(func)
    attrs = {
        "internal_task_name": internal_task_name,
        "run": run,
        "__module__": func.__module__,
        "__doc__": func.__doc__,
    }
    attrs.update(kwargs)

    return type(func.__name__, (task_class,), attrs)()


def task(queue, **headers):
    """decorator to add task to task registry"""
    from .base import BaseTask, CloudTaskWrapper
    def decorator(func):
        task_cls = create_task(BaseTask, func)
        registry.register(task_cls)

        @wraps(func)
        def inner_run(**kwargs):
            return CloudTaskWrapper(task_cls, queue, kwargs, headers=headers)

        return inner_run

    return decorator

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
                    logger.exception("Task scheduling failed. Retrying...")
                    time.sleep(retry_interval)
                    attempts_left -= 1

            # Limit exhausted
            error.args = ("Task scheduling limit exhausted",) + error.args
            raise error
        return wrapper

    return decorator
