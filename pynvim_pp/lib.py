from asyncio import AbstractEventLoop
from asyncio.events import get_running_loop
from concurrent.futures import Future, InvalidStateError
from contextlib import contextmanager, suppress
from functools import partial
from itertools import chain
from time import monotonic
from typing import Any, Awaitable, Callable, Iterator, TypeVar, cast
from unicodedata import east_asian_width

from pynvim import Nvim

from .consts import linesep
from .logging import with_suppress

_T = TypeVar("_T")

_UNICODE_WIDTH_LOOKUP = {
    "W": 2,  # CJK
    "N": 2,  # Non printable
}

_SPECIAL = {"\n", "\r"}


def display_width(text: str, tabsize: int) -> int:
    def cont() -> Iterator[int]:
        for char in text:
            if char == "\t":
                yield tabsize
            elif char in _SPECIAL:
                yield 2
            else:
                code = east_asian_width(char)
                yield _UNICODE_WIDTH_LOOKUP.get(code, 1)

    return sum(cont())


def go(nvim: Nvim, aw: Awaitable[_T], suppress: bool = True) -> Awaitable[_T]:
    async def wrapper() -> _T:
        with with_suppress(suppress):
            return await aw

    assert isinstance(nvim.loop, AbstractEventLoop)
    return nvim.loop.create_task(wrapper())


def threadsafe_call(nvim: Nvim, fn: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
    fut: Future = Future()

    def cont() -> None:
        try:
            ret = fn(*args, **kwargs)
        except Exception as e:
            with suppress(InvalidStateError):
                fut.set_exception(e)
        else:
            with suppress(InvalidStateError):
                fut.set_result(ret)

    nvim.async_call(cont)
    return cast(_T, fut.result())


async def async_call(
    nvim: Nvim, fn: Callable[..., _T], *args: Any, **kwargs: Any
) -> _T:
    loop = get_running_loop()
    fut: Future = Future()

    def cont() -> None:
        try:
            ret = fn(*args, **kwargs)
        except Exception as e:
            with suppress(InvalidStateError):
                fut.set_exception(e)
        else:
            with suppress(InvalidStateError):
                fut.set_result(ret)

    nvim.async_call(cont)
    return await loop.run_in_executor(None, fut.result)


def write(
    nvim: Nvim,
    val: Any,
    *vals: Any,
    sep: str = " ",
    error: bool = False,
) -> None:
    msg = sep.join(str(v) for v in chain((val,), vals))
    if nvim.funcs.has("nvim-0.5") and error:
        nvim.api.echo(((msg, "ErrorMsg"),), True, {})
    else:
        write = nvim.api.err_write if error else nvim.api.out_write
        write(msg=linesep)


def awrite(
    nvim: Nvim,
    val: Any,
    *vals: Any,
    sep: str = " ",
    end: str = linesep,
    error: bool = False,
) -> Awaitable[None]:
    p = partial(write, nvim, val, *vals, sep=sep, end=end, error=error)
    return go(nvim, aw=async_call(nvim, p))


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
