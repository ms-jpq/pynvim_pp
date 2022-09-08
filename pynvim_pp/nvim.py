from __future__ import annotations

from asyncio import gather
from contextlib import asynccontextmanager
from functools import cached_property, wraps
from inspect import iscoroutinefunction
from itertools import chain
from os.path import normpath
from pathlib import Path, PurePath
from string import ascii_uppercase
from sys import version_info
from typing import (
    Any,
    AsyncIterator,
    ByteString,
    Iterator,
    Mapping,
    NewType,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    cast,
)
from uuid import UUID

from msgpack import ExtType

from .atomic import Atomic
from .buffer import NS, Buffer
from .handler import GLOBAL_NS, RPC, RPCallable
from .lib import resolve_path
from .rpc import client
from .tabpage import Tabpage
from .types import (
    PARENT,
    Api,
    Callback,
    Chan,
    Ext,
    Fn,
    HasAPI,
    HasChan,
    NoneType,
    NvimError,
    NvimPos,
    Opts,
    RPCallable,
    RPClient,
    Vars,
)
from .window import Window

_LUA_EXEC = (PARENT / "exec.lua").read_text("utf-8")


_T = TypeVar("_T")

Marker = NewType("Marker", str)


class _CUR(HasAPI):
    prefix = "nvim"

    async def get_line(self) -> str:
        return await self.api.get_current_line(str)

    async def set_line(self, line: str) -> None:
        await self.api.set_current_line(NoneType, line)


class _LUA(HasAPI):
    prefix = "nvim"

    def __init__(self, chan: Chan, prefix: Sequence[str]) -> None:
        self._chan = chan
        self._prefix = prefix

    def __getattr__(self, attr: str) -> _LUA:
        return _LUA(chan=self._chan, prefix=(*self._prefix, attr))

    def __getitem__(self, attr: str) -> _LUA:
        return self.__getattr__(attr)

    async def __call__(self, ty: Type[_T], *params: Any) -> _T:
        def cont() -> Iterator[Any]:
            yield GLOBAL_NS
            yield ".".join(self._prefix)
            for param in params:
                if iscoroutinefunction(param):
                    fn = cast(RPCallable[Any], param)
                    yield {GLOBAL_NS: fn.uuid}
                else:
                    yield param

        return await self.api.exec_lua(ty, _LUA_EXEC, tuple(cont()))


class _Wrap(RPClient):
    def __init__(self, rpc: RPClient) -> None:
        self._rpc = rpc
        self._mapping = {ext.code: ext for ext in (Buffer, Window, Tabpage)}

    def _unpack(self, val: Any) -> Any:
        if isinstance(val, Sequence) and not isinstance(val, (str, ByteString)):
            return tuple(map(self._unpack, val))
        if isinstance(val, Mapping):
            return {k: self._unpack(v) for k, v in val.items()}
        if isinstance(val, ExtType):
            v = cast(Any, val)
            return self._mapping[v.code](data=v.data)
        else:
            return val

    def _pack(self, val: Any) -> Any:
        if isinstance(val, Sequence) and not isinstance(val, (str, ByteString)):
            return tuple(map(self._unpack, val))
        if isinstance(val, Mapping):
            return {k: self._unpack(v) for k, v in val.items()}
        if isinstance(val, Ext):
            return ExtType(val.code, val.data)
        else:
            return val

    async def notify(self, method: str, *params: Any) -> None:
        await self._rpc.notify(method, *map(self._pack, params))

    async def request(self, method: str, *params: Any) -> Sequence[Any]:
        resp = await self._rpc.request(method, *map(self._pack, params))
        return tuple(map(self._unpack, resp))

    def on_callback(self, method: str, f: Callback) -> None:
        @wraps(f)
        async def ff(*params: Any) -> Any:
            return await f(*map(self._unpack, params))

        self._rpc.on_callback(method, f=ff)


class _Nvim(HasAPI, HasChan):
    prefix = "nvim"
    chan = cast(Chan, None)

    @cached_property
    def lua(self) -> _LUA:
        return _LUA(chan=self.chan, prefix=())

    @cached_property
    def fn(self) -> Fn:
        return Fn(api=self.api)

    @cached_property
    def vars(self) -> Vars:
        return Vars(api=self.api)

    @cached_property
    def opts(self) -> Opts:
        return Opts(api=self.api)

    @cached_property
    def current(self) -> _CUR:
        return _CUR()

    async def size(self) -> Tuple[int, int]:
        with Atomic() as (atomic, ns):
            ns.rows = atomic.get_option("lines")
            ns.cols = atomic.get_option("columns")
            await atomic.commit(NoneType)

        rows, cols = ns.rows(int), ns.cols(int)
        return rows, cols

    async def write(
        self,
        val: Any,
        *vals: Any,
        sep: str = " ",
        error: bool = False,
    ) -> None:
        msg = sep.join(str(v) for v in chain((val,), vals)).rstrip()
        if self.api.has("nvim-0.5"):
            a = (msg, "ErrorMsg") if error else (msg,)
            await self.api.echo(NoneType, (a,), True, {})
        else:
            write = self.api.err_write if error else self.api.out_write
            await write(NoneType, msg + "\n")

    async def getcwd(self) -> Path:
        cwd = await self.fn.getcwd(str)
        return Path(normpath(cwd))

    async def chdir(self, path: PurePath, history: bool = True) -> None:
        if history:
            escaped = await self.fn.fnameescape(str, normpath(path))
            await self.api.command(NoneType, f"chdir {escaped}")
        else:
            await self.api.set_current_dir(NoneType, normpath(path))

    async def list_runtime_paths(self) -> Sequence[Path]:
        with Atomic() as (atomic, ns):
            ns.cwd = atomic.call_function("getcwd", ())
            ns.paths = atomic.list_runtime_paths()
            await atomic.commit(NoneType)

        cwd = Path(normpath(ns.cwd(str)))
        paths = cast(Sequence[str], ns.paths(NoneType))
        resolved = await gather(*(resolve_path(cwd, path=path) for path in paths))
        return tuple(path for path in resolved if path)

    async def create_namespace(self, seed: UUID) -> NS:
        ns = await self.api.create_namespace(int, seed.hex)
        return NS(ns)

    async def list_bookmarks(self) -> Mapping[Marker, Tuple[Path, NvimPos]]:
        if await self.api.has("nvim-0.6"):
            with Atomic() as (atomic, ns):
                ns.cwd = atomic.call_function("getcwd", ())
                for mark_id in ascii_uppercase:
                    atomic.get_mark(mark_id, {})
                pwd, *marks = cast(Any, await atomic.commit(NoneType))

            cwd = Path(cast(str, pwd))
            marks = cast(Sequence[Tuple[int, int, Buffer, str]], marks)

            acc = {
                Marker(marker): (path, (row, col))
                for marker, (row, col, _, path) in zip(ascii_uppercase, marks)
                if (row, col) != (0, 0)
            }
            paths = await gather(
                *(resolve_path(cwd, path=path) for path, _ in acc.values())
            )
            resolved = {
                marker: (path, pos)
                for (marker, (_, pos)), path in zip(acc.items(), paths)
            }
            return resolved
        else:
            return {}

    async def input(self, question: str, default: str) -> Optional[str]:
        try:
            resp = cast(Optional[str], await self.fn.input(NoneType, question, default))
        except NvimError:
            return None
        else:
            return resp

    async def input_list(self, choices: Mapping[str, _T]) -> Optional[_T]:
        try:
            idx = cast(
                Optional[int], await self.fn.inputlist(NoneType, tuple(choices.keys()))
            )
        except NvimError:
            return None
        else:
            for i, val in enumerate(choices.values()):
                if i == idx:
                    return val
            else:
                return None

    async def confirm(
        self, question: str, answers: str, answer_key: Mapping[int, _T]
    ) -> Optional[_T]:
        try:
            resp = cast(
                Optional[int], await self.fn.confirm(NoneType, question, answers, 0)
            )
        except NvimError:
            return None
        else:
            return answer_key.get(resp or -1)


@asynccontextmanager
async def conn(socket: PurePath) -> AsyncIterator[RPClient]:
    async with client(socket) as rpc:
        await rpc.notify(
            "nvim_set_client_info",
            PARENT.name,
            {
                "major": version_info.major,
                "minor": version_info.minor,
                "patch": version_info.micro,
            },
            "remote",
            (),
            {},
        )
        chan, meta = await rpc.request("nvim_get_api_info")

        assert isinstance(meta, Mapping)
        types = meta["types"]
        assert isinstance(types, Mapping)

        Buffer.init_code(code=types["Buffer"]["id"])
        Window.init_code(code=types["Window"]["id"])
        Tabpage.init_code(code=types["Tabpage"]["id"])

        wrapped = _Wrap(rpc=rpc)

        for cls in (_Nvim, Atomic, Buffer, Window, Tabpage, _LUA, _CUR):
            c = cast(HasAPI, cls)
            api = Api(rpc=wrapped, prefix=c.prefix)
            c.init_api(api=api)

        ch = Chan(chan)
        for cls in (_Nvim, RPC):
            c = cast(HasChan, cls)
            c.init_chan(chan=ch)

        yield wrapped


Nvim = _Nvim()
