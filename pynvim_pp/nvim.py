from __future__ import annotations

from asyncio import gather
from contextlib import asynccontextmanager
from functools import cached_property
from inspect import iscoroutinefunction
from itertools import chain
from os.path import normpath
from pathlib import Path, PurePath
from string import ascii_uppercase
from typing import (
    Any,
    AsyncIterator,
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

from .atomic import Atomic
from .buffer import Buffer
from .handler import GLOBAL_NS, RPC, RPCallable
from .lib import decode, resolve_path
from .rpc import RPCdefault, ServerAddr, client
from .tabpage import Tabpage
from .types import (
    PARENT,
    Api,
    BufNamespace,
    CastReturnAF,
    Chan,
    HasApi,
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

_LUA_EXEC = decode((PARENT / "exec.lua").read_bytes().strip())


_T = TypeVar("_T")

Marker = NewType("Marker", str)


class _Cur(HasApi):
    async def get_line(self) -> str:
        return await self.api.get_current_line(str)

    async def set_line(self, line: str) -> None:
        await self.api.set_current_line(NoneType, line)


class _Vvars(HasApi):
    async def get(self, ty: Type[_T], key: str) -> _T:
        return await self.api.get_var(ty, key)


class _Fn(HasApi):
    def __getattr__(self, attr: str) -> CastReturnAF:
        async def cont(ty: Type[_T], *params: Any) -> _T:
            return await self.api.call_function(ty, attr, params)

        return cont

    def __getitem__(self, attr: str) -> CastReturnAF:
        return self.__getattr__(attr)


class _Lua(HasApi, HasChan):
    def __init__(self, prefix: Sequence[str]) -> None:
        self._prefix = prefix

    def __getattr__(self, attr: str) -> _Lua:
        return _Lua(prefix=(*self._prefix, attr))

    def __getitem__(self, attr: str) -> _Lua:
        return self.__getattr__(attr)

    async def __call__(self, ty: Type[_T], *params: Any, schedule: bool = False) -> _T:
        def cont() -> Iterator[Any]:
            yield GLOBAL_NS
            yield schedule
            yield ".".join(self._prefix)
            for param in params:
                if iscoroutinefunction(param):
                    fn = cast(RPCallable[Any], param)
                    yield {GLOBAL_NS: fn.uuid}
                else:
                    yield param

        return await self.api.execute_lua(ty, _LUA_EXEC, tuple(cont()))


class _Nvim(HasApi, HasChan):
    chan = cast(Chan, None)

    def __init__(self) -> None:
        self.lua = _Lua(prefix=())
        self.fn = _Fn()
        self.vvars = _Vvars()
        self.current = _Cur()

    @cached_property
    def opts(self) -> Opts:
        return Opts(api=self.api, this=None)

    @cached_property
    def vars(self) -> Vars:
        return Vars(api=self.api, this=None)

    async def exec(self, viml: str) -> str:
        return await self.api.command(str, viml)

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
        if await self.api.has("nvim-0.5"):
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

    async def create_namespace(self, seed: UUID) -> BufNamespace:
        ns = await self.api.create_namespace(BufNamespace, seed.hex)
        return ns

    async def list_bookmarks(
        self,
    ) -> Mapping[Marker, Tuple[Optional[Path], Optional[Buffer], NvimPos]]:
        if await self.api.has("nvim-0.6"):
            with Atomic() as (atomic, ns):
                ns.cwd = atomic.call_function("getcwd", ())
                for mark_id in ascii_uppercase:
                    atomic.get_mark(mark_id, {})
                pwd, *marks = cast(Any, await atomic.commit(NoneType))

            cwd = Path(cast(str, pwd))
            marks = cast(Sequence[Tuple[int, int, int, str]], marks)

            acc = {
                Marker(marker): (
                    path,
                    Buffer.from_int(bufnr) if bufnr != 0 else None,
                    (row - 1, col),
                )
                for marker, (row, col, bufnr, path) in zip(ascii_uppercase, marks)
                if (row, col) != (0, 0)
            }
            paths = await gather(
                *(resolve_path(cwd, path=path) for path, _, _ in acc.values())
            )
            resolved = {
                marker: (path, buf, pos)
                for (marker, (_, buf, pos)), path in zip(acc.items(), paths)
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

    async def input_list(
        self, choices: Mapping[str, _T], start: int = 1
    ) -> Optional[_T]:
        try:
            idx = cast(
                Optional[int], await self.fn.inputlist(NoneType, tuple(choices.keys()))
            )
        except NvimError:
            return None
        else:
            for i, val in enumerate(choices.values(), start=start):
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
async def conn(socket: ServerAddr, default: RPCdefault) -> AsyncIterator[RPClient]:
    async with client(socket, default=default) as rpc:
        for cls in (_Nvim, Atomic, Buffer, Window, Tabpage, _Lua, _Fn, _Vvars, _Cur):
            c = cast(HasApi, cls)
            api = Api(rpc=rpc, prefix=c.prefix)
            c.init_api(api=api)

        for cls in (_Nvim, _Lua, RPC):
            cl = cast(HasChan, cls)
            cl.init_chan(chan=rpc.chan)

        yield rpc


Nvim = _Nvim()
