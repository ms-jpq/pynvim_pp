from abc import abstractmethod
from os import linesep
from pathlib import Path
from string import Template
from typing import (
    Any,
    Awaitable,
    Callable,
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
from uuid import UUID

from .lib import decode

NoneType = bool
_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)

PARENT = Path(__file__).resolve(strict=True).parent

_LUA_CALL = Template(decode((PARENT / "call.lua").read_bytes().strip()))


class NvimError(Exception):
    ...


Chan = NewType("Chan", int)
Callback = Callable[..., Awaitable[Any]]


class CastReturnAF(Protocol):
    async def __call__(self, ty: Type[_T], *args: Any) -> _T:
        ...


class ApiReturnAF(Protocol):
    async def __call__(
        self, ty: Type[_T], *args: Any, prefix: Optional[str] = None
    ) -> _T:
        ...


NvimPos = Tuple[int, int]


class RPCallable(Protocol[_T_co]):
    @property
    def uuid(self) -> UUID:
        ...

    @property
    def blocking(self) -> bool:
        ...

    @property
    def schedule(self) -> bool:
        ...

    @property
    def namespace(self) -> str:
        ...

    @property
    def name(self) -> str:
        ...

    async def __call__(self, *args: Any, **kwargs: Any) -> Awaitable[_T_co]:
        ...


class RPClient(Protocol):
    @property
    @abstractmethod
    def chan(self) -> Chan:
        ...

    @abstractmethod
    async def notify(self, method: str, *params: Any) -> None:
        ...

    @abstractmethod
    async def request(self, method: str, *params: Any) -> Any:
        ...

    @abstractmethod
    def on_callback(self, method: str, f: Callback) -> None:
        ...


class Api:
    _features: MutableMapping[str, bool] = {}

    def __init__(self, rpc: RPClient, prefix: str) -> None:
        self._rpc = rpc
        self.prefix = prefix

    def __getattr__(self, attr: str) -> ApiReturnAF:
        async def cont(ty: Type[_T], *params: Any, prefix: Optional[str] = None) -> _T:
            method = f"{prefix or self.prefix}_{attr}"
            resp = await self._rpc.request(method, *params)
            return cast(_T, resp)

        return cont

    async def has(self, feature: str) -> bool:
        if (has := self._features.get(feature)) is not None:
            return has
        else:
            has = await self._rpc.request("nvim_call_function", "has", (feature,))
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


class HasLocalCall(HasApi):
    async def local_lua(self, ty: Type[_T], lua: str, *argv: Any) -> _T:
        fn = _LUA_CALL.substitute(BODY=linesep + lua)
        return await self.api.exec_lua(ty, fn, (self.prefix, self, *argv))


class HasChan:
    chan = cast(Chan, None)

    @classmethod
    def init_chan(cls, chan: Chan) -> None:
        cls.chan = chan


class Ext(HasApi):
    code = cast(int, None)

    @classmethod
    def init_code(cls, code: int) -> None:
        assert isinstance(code, int)
        cls.code = code

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.vars = Vars(self.api, this=self)
        self.opts = Opts(self.api, this=self)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Ext):
            return self.code == other.code and self.data == other.data
        else:
            return False

    def __hash__(self) -> int:
        return hash((self.code, self.data))
