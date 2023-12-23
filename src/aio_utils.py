# code taken from https://stackoverflow.com/a/69514930/6946463

import asyncio
import platform
from typing import Awaitable, TypeVar

import nest_asyncio

T = TypeVar("T")


if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def asyncio_run(future: Awaitable, as_task=True) -> T:
    """
    A better implementation of `asyncio.run`.

    Args:
        future: A future or task or call of an async method.
        as_task: Forces the future to be scheduled as task (needed for e.g. aiohttp).
    """
    # from https://stackoverflow.com/a/63593839/6946463
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # no event loop running:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(_to_task(future, as_task, loop))
    else:
        nest_asyncio.apply(loop)
        return asyncio.run(_to_task(future, as_task, loop))


def asyncio_gather(*futures, return_exceptions=False) -> asyncio.Future[list]:
    """
    A version of asyncio.gather that runs on the internal event loop
    Args:
        *futures (any):
        return_exceptions (bool): If false, an error in any one task will end all tasks and return an error. If true, errors will be returned
                                  for the errors as if they were successful. Defaults to False.
    """
    return asyncio.gather(*futures, return_exceptions=return_exceptions)


def _to_task(future, as_task, loop):
    if not as_task or isinstance(future, asyncio.Task):
        return future
    return loop.create_task(future)
