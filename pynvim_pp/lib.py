from asyncio import AbstractEventLoop
from concurrent.futures import Future, InvalidStateError
from contextlib import contextmanager, suppress
from functools import lru_cache, partial
from itertools import chain
from os import PathLike, name
from os.path import normcase
from pathlib import Path
from string import ascii_lowercase
from time import monotonic
from typing import (
    Any,
    Awaitable,
    Callable,
    Iterator,
    Literal,
    Optional,
    TypeVar,
    Union,
    cast,
)
from unicodedata import east_asian_width
from urllib.parse import urlsplit

from pynvim import Nvim

from .logging import with_suppress

_T = TypeVar("_T")

_UNICODE_WIDTH_LOOKUP = {
    "W": 2,  # CJK
    "N": 2,  # Non printable
}

_SPECIAL = {"\n", "\r"}


@lru_cache(maxsize=None)
def nvim_has(nvim: Nvim, feature: str) -> bool:
    return nvim.funcs.has(feature)


def encode(text: str, encoding: Literal["UTF-8", "UTF-16-LE"] = "UTF-8") -> bytes:
    return text.encode(encoding, errors="surrogateescape")


def decode(btext: bytes, encoding: Literal["UTF-8", "UTF-16-LE"] = "UTF-8") -> str:
    return btext.decode(encoding, errors="surrogateescape")


def recode(text: str) -> str:
    return text.encode("UTF-8", errors="ignore").decode("UTF-8")


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
    assert isinstance(nvim.loop, AbstractEventLoop)
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
    return await nvim.loop.run_in_executor(None, fut.result)


def write(
    nvim: Nvim,
    val: Any,
    *vals: Any,
    sep: str = " ",
    error: bool = False,
) -> None:
    msg = sep.join(str(v) for v in chain((val,), vals)).rstrip()
    if nvim_has(nvim, "nvim-0.5"):
        a = (msg, "ErrorMsg") if error else (msg,)
        nvim.api.echo((a,), True, {})
    else:
        write = nvim.api.err_write if error else nvim.api.out_write
        write(msg + "\n")


def awrite(
    nvim: Nvim,
    val: Any,
    *vals: Any,
    sep: str = " ",
    error: bool = False,
) -> Awaitable[None]:
    p = partial(write, nvim, val, *vals, sep=sep, error=error)
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


def _expanduser(path: Path) -> Path:
    try:
        resolved = path.expanduser()
    except RuntimeError:
        return path
    else:
        return resolved


def _safe_path(path: Union[PathLike, str]) -> Optional[Path]:
    p = normcase(path)
    try:
        parsed = urlsplit(p, allow_fragments=False)
    except ValueError:
        return None
    else:
        scheme = parsed.scheme.casefold()
        if scheme in {"", "file"}:
            safe_path = Path(normcase(parsed.path))
            return safe_path
        elif name == "nt" and scheme in {*ascii_lowercase}:
            return Path(p)
        else:
            return None


def resolve_path(cwd: Optional[Path], path: Union[PathLike, str]) -> Optional[Path]:
    if not (safe_path := _safe_path(path)):
        return None
    elif safe_path.is_absolute():
        return safe_path
    elif (resolved := _expanduser(safe_path)) != safe_path:
        return resolved
    elif cwd:
        return cwd / path
    else:
        return None
