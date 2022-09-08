from __future__ import annotations

from inspect import iscoroutinefunction
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Mapping,
    MutableMapping,
    Optional,
    Tuple,
    TypeVar,
    cast,
)
from uuid import uuid4

from .atomic import Atomic
from .lib import decode
from .types import PARENT, Chan, HasChan, RPCallable

_T = TypeVar("_T")


GLOBAL_NS = str(uuid4())

_LUA_PRC = decode((PARENT / "rpc.lua").read_bytes().strip())


def _new_lua_func(atomic: Atomic, chan: Chan, handler: RPCallable[Any]) -> None:
    method = "rpcrequest" if handler.blocking else "rpcnotify"
    atomic.exec_lua(
        _LUA_PRC,
        (GLOBAL_NS, method, chan, str(handler.uuid), handler.namespace, handler.name),
    )


def _new_viml_func(atomic: Atomic, handler: RPCallable[Any]) -> None:
    viml = f"""
    function! {handler.name}(...)
      return luaeval('_G["{GLOBAL_NS}"]["{handler.uuid}"](unpack(_A))', a:000)
    endfunction
    """
    atomic.command(viml)


def _name_gen(fn: Callable[..., Awaitable[Any]]) -> str:
    return f"{fn.__module__}.{fn.__qualname__}".replace(".", "_").capitalize()


class RPC(HasChan):
    def __init__(
        self,
        namespace: str,
        name_gen: Callable[[Callable[..., Awaitable[Any]]], str] = _name_gen,
    ) -> None:
        self._handlers: MutableMapping[str, RPCallable[Any]] = {}
        self._namespace = namespace
        self._name_gen = name_gen

    def __call__(
        self,
        blocking: bool,
        name: Optional[str] = None,
    ) -> Callable[[Callable[..., Coroutine[Any, Any, _T]]], RPCallable[_T]]:
        def decor(handler: Callable[..., Coroutine[Any, Any, _T]]) -> RPCallable[_T]:
            assert iscoroutinefunction(handler)
            h_name = name or self._name_gen(cast(Any, handler))

            setattr(handler, "uuid", uuid4())
            setattr(handler, "blocking", blocking)
            setattr(handler, "namespace", self._namespace)
            setattr(handler, "name", h_name)

            self._handlers[h_name] = cast(RPCallable, handler)
            return cast(RPCallable[_T], cast(Any, handler))

        return decor

    def drain(self) -> Tuple[Atomic, Mapping[str, RPCallable[Any]]]:
        atomic = Atomic()
        specs: MutableMapping[str, RPCallable[Any]] = {}
        while self._handlers:
            name, handler = self._handlers.popitem()
            _new_lua_func(atomic, chan=self.chan, handler=handler)
            _new_viml_func(atomic, handler=handler)
            specs[name] = handler

        return atomic, specs
