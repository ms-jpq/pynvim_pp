from __future__ import annotations

from asyncio.coroutines import iscoroutinefunction
from textwrap import dedent
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from pynvim import Nvim

from .atomic import Atomic
from .logging import log

T = TypeVar("T")

RpcMsg = Tuple[str, Sequence[Sequence[Any]]]


class RpcCallable(Generic[T]):
    def __init__(
        self,
        name: str,
        blocking: bool,
        handler: Union[Callable[..., T], Callable[..., Awaitable[T]]],
    ) -> None:
        self.is_async = iscoroutinefunction(handler)
        if self.is_async and blocking:
            raise ValueError()
        else:
            self.name = name
            self.is_blocking = blocking
            self._handler = handler

    def __call__(self, nvim: Nvim, *args: Any, **kwargs: Any) -> Union[T, Awaitable[T]]:
        if self.is_async:
            aw = cast(Awaitable[T], self._handler(nvim, *args, **kwargs))
            return aw
        else:
            return cast(T, self._handler(nvim, *args, **kwargs))


RpcSpec = Tuple[str, RpcCallable[Any]]


def _new_lua_func(chan: int, handler: RpcCallable[Any]) -> str:
    op = "rpcrequest" if handler.is_blocking else "rpcnotify"
    lua = f"""
    (function()
      {handler.name} = function(...)
        return vim.api.nvim_call_function("{op}", {{{chan}, "{handler.name}", {{...}}}})
      end
    end)()
    """
    return dedent(lua)


def _new_viml_func(handler: RpcCallable[Any]) -> str:
    viml = f"""
    function! {handler.name}(...)
      return luaeval('{handler.name}(...)', [a:000])
    endfunction
    """
    return dedent(viml)


def _name_gen(fn: Callable[..., Any]) -> str:
    return f"{fn.__module__}.{fn.__qualname__}".replace(".", "_").capitalize()


class RPC:
    def __init__(
        self, name_gen: Callable[[Callable[..., Any]], str] = _name_gen
    ) -> None:
        self._handlers: MutableMapping[str, RpcCallable[Any]] = {}
        self._name_gen = name_gen

    def __call__(
        self,
        blocking: bool,
        name: Optional[str] = None,
    ) -> Callable[[Callable[..., T]], RpcCallable[T]]:
        def decor(handler: Callable[..., T]) -> RpcCallable[T]:
            c_name = name if name else self._name_gen(handler)

            wraped = RpcCallable(name=c_name, blocking=blocking, handler=handler)
            self._handlers[wraped.name] = wraped
            return wraped

        return decor

    def drain(self, chan: int) -> Tuple[Atomic, Sequence[RpcSpec]]:
        atomic = Atomic()
        specs: MutableSequence[RpcSpec] = []
        while self._handlers:
            name, handler = self._handlers.popitem()
            atomic.call_function(_new_lua_func(chan, handler=handler), ())
            atomic.command(_new_viml_func(handler=handler))
            specs.append((name, handler))

        return atomic, specs


def nil_handler(name: str) -> RpcCallable:
    def handler(nvim: Nvim, *args: Any, **kwargs: Any) -> None:
        log.warn("MISSING RPC HANDLER FOR: %s - %s - %s", name, args, kwargs)

    return RpcCallable(name=name, blocking=True, handler=handler)

