from asyncio.events import get_running_loop
from asyncio.tasks import create_task
from concurrent.futures import Future
from contextlib import contextmanager
from functools import partial
from itertools import chain
from time import monotonic
from typing import Any, Awaitable, Callable, Iterator, TypeVar, cast

from pynvim import Nvim

from .consts import linesep
from .logging import log

T = TypeVar("T")


def go(aw: Awaitable[T]) -> Awaitable[T]:
    async def wrapper() -> T:
        try:
            return await aw
        except Exception as e:
            log.exception("%s", e)
            raise

    return create_task(wrapper())


def threadsafe_call(nvim: Nvim, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    fut: Future = Future()

    def cont() -> None:
        try:
            ret = fn(*args, **kwargs)
        except Exception as e:
            if not fut.cancelled():
                fut.set_exception(e)
        else:
            if not fut.cancelled():
                fut.set_result(ret)

    nvim.async_call(cont)
    return cast(T, fut.result())


async def async_call(nvim: Nvim, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    loop = get_running_loop()
    fut: Future = Future()

    def cont() -> None:
        try:
            ret = fn(*args, **kwargs)
        except Exception as e:
            if not fut.cancelled():
                fut.set_exception(e)
        else:
            if not fut.cancelled():
                fut.set_result(ret)

    nvim.async_call(cont)
    return await loop.run_in_executor(None, fut.result)


def write(
    nvim: Nvim,
    val: Any,
    *vals: Any,
    sep: str = " ",
    end: str = linesep,
    error: bool = False,
) -> None:
    write = nvim.api.err_write if error else nvim.api.out_write
    msg = sep.join(str(v) for v in chain((val,), vals)) + end
    write(msg)


def awrite(
    nvim: Nvim,
    val: Any,
    *vals: Any,
    sep: str = " ",
    end: str = linesep,
    error: bool = False,
) -> Awaitable[None]:
    p = partial(write, nvim, val, *vals, sep=sep, end=end, error=error)
    return go(async_call(nvim, p))


@contextmanager
def bench(
    nvim: Nvim, *args: Any, threshold: float = 0.01, precision: int = 3
) -> Iterator[None]:
    t1 = monotonic()
    yield None
    t2 = monotonic()
    elapsed = t2 - t1
    if elapsed >= threshold:
        write(nvim, *args, round(elapsed, precision))
