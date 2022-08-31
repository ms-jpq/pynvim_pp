from __future__ import annotations

from inspect import iscoroutinefunction
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Callable,
    Mapping,
    MutableMapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    cast,
)
from uuid import UUID, uuid4

from .atomic import Atomic

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)

RpcMsg = Tuple[str, Sequence[Any]]

GLOBAL_NS = str(uuid4())

_LUA_PRC = (Path(__file__).resolve(strict=True).parent / "rpc.lua").read_text("utf-8")


class RPCallable(Protocol[_T_co]):
    @property
    def uuid(self) -> UUID:
        ...

    @property
    def blocking(self) -> bool:
        ...

    @property
    def namespace(self) -> str:
        ...

    @property
    def name(self) -> str:
        ...

    async def __call__(self, *args: Any, **kwargs: Any) -> Awaitable[_T_co]:
        ...


def _new_lua_func(atomic: Atomic, chan: int, handler: RPCallable[Any]) -> None:
    method = "rpcrequest" if handler.blocking else "rpcnotify"
    atomic.exec_lua(
        _LUA_PRC,
        (GLOBAL_NS, method, chan, handler.uuid, handler.namespace, handler.name),
    )


def _new_viml_func(atomic: Atomic, handler: RPCallable[Any]) -> None:
    viml = f"""
    function! {handler.name}(...)
      return luaeval('return _G["{handler.namespace}"]["{handler.name}"](unpack(...))', a:000)
    endfunction
    """
    atomic.command(viml)


def _name_gen(fn: Callable[..., Awaitable[Any]]) -> str:
    return f"{fn.__module__}.{fn.__qualname__}".replace(".", "_").capitalize()


class RPC:
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
    ) -> Callable[[_T], _T]:
        def decor(handler: _T) -> _T:
            assert iscoroutinefunction(handler)
            h_name = name or self._name_gen(cast(Any, handler))

            setattr(handler, "uuid", uuid4())
            setattr(handler, "blocking", blocking)
            setattr(handler, "namespace", self._namespace)
            setattr(handler, "name", h_name)

            self._handlers[h_name] = cast(RPCallable, handler)
            return cast(_T, cast(Any, handler))

        return decor

    def drain(self, chan: int) -> Tuple[Atomic, Mapping[str, RPCallable[Any]]]:
        atomic = Atomic()
        specs: MutableMapping[str, RPCallable[Any]] = {}
        while self._handlers:
            name, handler = self._handlers.popitem()
            _new_lua_func(atomic, chan=chan, handler=handler)
            _new_viml_func(atomic, handler=handler)
            specs[name] = handler

        return atomic, specs
