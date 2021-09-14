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

_T = TypeVar("_T")

RpcMsg = Tuple[str, Sequence[Sequence[Any]]]


class RpcCallable(Generic[_T]):
    def __init__(
        self,
        namespace: str,
        name: str,
        blocking: bool,
        schedule: bool,
        handler: Union[Callable[..., _T], Callable[..., Awaitable[_T]]],
    ) -> None:
        self.is_async = iscoroutinefunction(handler)
        if self.is_async and blocking:
            raise ValueError()
        else:
            self._namespace = namespace
            self.name = name
            self.is_blocking = blocking
            self._schedule = schedule
            self._handler = handler

    def __call__(
        self, nvim: Nvim, *args: Any, **kwargs: Any
    ) -> Union[_T, Awaitable[_T]]:
        if self.is_async:
            aw = cast(Awaitable[_T], self._handler(nvim, *args, **kwargs))
            return aw
        else:
            return cast(_T, self._handler(nvim, *args, **kwargs))


RpcSpec = Tuple[str, RpcCallable[Any]]


def _new_lua_func(atomic: Atomic, chan: int, handler: RpcCallable[Any]) -> None:
    op = "rpcrequest" if handler.is_blocking else "rpcnotify"

    if handler._schedule:
        lua = """
        (function(op, chan, ns, name)
          _G[ns] = _G[ns] or {}
          _G[ns][name] = function(...)
            local args = {...}
            vim.schedule(function()
              return vim.api.nvim_call_function(op, vim.tbl_flatten{{chan, name}, args})
            end)
          end
        end)(...)
        """
    else:
        lua = """
        (function(op, chan, ns, name)
          _G[ns] = _G[ns] or {}
          _G[ns][name] = function(...)
            local args = {...}
            return vim.api.nvim_call_function(op, vim.tbl_flatten{{chan, name}, args})
          end
        end)(...)
        """

    atomic.execute_lua(
        lua,
        (op, chan, handler._namespace, handler.name),
    )


def _new_viml_func(atomic: Atomic, handler: RpcCallable[Any]) -> None:
    viml = f"""
    function! {handler.name}(...)
      return nvim_execute_lua('_G["{handler._namespace}"]["{handler.name}"](...)', a:000)
    endfunction
    """
    atomic.command(viml)


def _name_gen(fn: Callable[..., Any]) -> str:
    return f"{fn.__module__}.{fn.__qualname__}".replace(".", "_").capitalize()


class RPC:
    def __init__(
        self, namespace: str, name_gen: Callable[[Callable[..., Any]], str] = _name_gen
    ) -> None:
        self._handlers: MutableMapping[str, RpcCallable[Any]] = {}
        self._namespace = namespace
        self._name_gen = name_gen

    def __call__(
        self,
        blocking: bool,
        schedule: bool = False,
        name: Optional[str] = None,
    ) -> Callable[[Callable[..., _T]], RpcCallable[_T]]:
        def decor(handler: Callable[..., _T]) -> RpcCallable[_T]:
            c_name = name if name else self._name_gen(handler)

            wraped = RpcCallable(
                namespace=self._namespace,
                name=c_name,
                blocking=blocking,
                schedule=schedule,
                handler=handler,
            )
            self._handlers[wraped.name] = wraped
            return wraped

        return decor

    def drain(self, chan: int) -> Tuple[Atomic, Sequence[RpcSpec]]:
        atomic = Atomic()
        specs: MutableSequence[RpcSpec] = []
        while self._handlers:
            name, handler = self._handlers.popitem()
            _new_lua_func(atomic, chan=chan, handler=handler)
            _new_viml_func(atomic, handler=handler)
            specs.append((name, handler))

        return atomic, specs


def nil_handler(name: str) -> RpcCallable:
    def handler(nvim: Nvim, *args: Any, **kwargs: Any) -> None:
        log.warn("MISSING RPC HANDLER FOR: %s - %s - %s", name, args, kwargs)

    nil = RpcCallable(
        namespace="",
        name=name,
        blocking=True,
        schedule=False,
        handler=handler,
    )
    return nil
