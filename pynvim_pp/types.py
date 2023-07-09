from functools import cached_property
from os import linesep
from pathlib import Path
from string import Template
from typing import (
    Any,
    Iterator,
    MutableMapping,
    NewType,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    cast,
)

from .lib import decode
from .rpc_types import Chan, Method, RPClient

NoneType = bool
_T = TypeVar("_T")

PARENT = Path(__file__).resolve(strict=True).parent

_LUA_CALL = Template(decode((PARENT / "call.lua").read_bytes().strip()))


BufNamespace = NewType("BufNamespace", int)
NvimPos = Tuple[int, int]


class CastReturnAF(Protocol):
    async def __call__(self, ty: Type[_T], *args: Any) -> _T:
        ...


class ApiReturnAF(Protocol):
    async def __call__(
        self, ty: Type[_T], *args: Any, prefix: Optional[str] = None
    ) -> _T:
        ...


class Api:
    _features: MutableMapping[str, bool] = {}

    def __init__(self, rpc: RPClient, prefix: str) -> None:
        self._rpc = rpc
        self.prefix = prefix

    def __getattr__(self, attr: str) -> ApiReturnAF:
        async def cont(ty: Type[_T], *params: Any, prefix: Optional[str] = None) -> _T:
            method = Method(f"{prefix or self.prefix}_{attr}")
            resp = await self._rpc.request(method, *params)
            return cast(_T, resp)

        return cont

    async def has(self, feature: str) -> bool:
        if (has := self._features.get(feature)) is not None:
            return has
        else:
            has = await self._rpc.request(
                Method("nvim_call_function"), "has", (feature,)
            )
            self._features[feature] = has
            return has


class _ApiTargeted:
    def __init__(self, api: Api, this: Optional[Any]) -> None:
        self._api, self._this = api, this

    def _that(self) -> Iterator[Any]:
        if self._this:
            yield self._this


class Vars(_ApiTargeted):
    async def has(self, key: str) -> bool:
        try:
            await self._api.get_var(NoneType, *self._that(), key)
        except Exception:
            return False
        else:
            return True

    async def get(self, ty: Type[_T], key: str) -> Optional[_T]:
        try:
            return await self._api.get_var(ty, *self._that(), key)
        except Exception:
            return None

    async def set(self, key: str, val: Any) -> None:
        await self._api.set_var(NoneType, *self._that(), key, val)

    async def delete(self, key: str) -> None:
        await self._api.del_var(NoneType, *self._that(), key)


class Opts(_ApiTargeted):
    async def get(self, ty: Type[_T], key: str) -> _T:
        return await self._api.get_option(ty, *self._that(), key)

    async def set(self, key: str, val: Any) -> None:
        await self._api.set_option(NoneType, *self._that(), key, val)


class HasApi:
    base_prefix = "nvim"
    prefix = base_prefix
    api = cast(Api, None)

    @classmethod
    def init_api(cls, api: Api) -> None:
        cls.api = api


class HasChan:
    chan = cast(Chan, None)

    @classmethod
    def init_chan(cls, chan: Chan) -> None:
        cls.chan = chan


class HasVOL(HasApi):
    @cached_property
    def vars(self) -> Vars:
        return Vars(self.api, this=self)

    @cached_property
    def opts(self) -> Opts:
        return Opts(self.api, this=self)

    async def local_lua(self, ty: Type[_T], lua: str, *argv: Any) -> _T:
        fn = _LUA_CALL.substitute(BODY=linesep + lua)
        return await self.api.execute_lua(ty, fn, (self.prefix, self, *argv))
