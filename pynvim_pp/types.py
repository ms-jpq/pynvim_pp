from abc import abstractmethod
from functools import cached_property
from typing import (
    Any,
    Awaitable,
    Callable,
    MutableMapping,
    NewType,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    cast,
)
from uuid import UUID

NoneType = bool
_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)


Chan = NewType("Chan", int)
Callback = Callable[..., Awaitable[Any]]


class CastReturnAF(Protocol):
    async def __call__(self, ty: Type[_T], *args: Any) -> _T:
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
    def namespace(self) -> str:
        ...

    @property
    def name(self) -> str:
        ...

    async def __call__(self, *args: Any, **kwargs: Any) -> Awaitable[_T_co]:
        ...


class RPClient(Protocol):
    @abstractmethod
    async def notify(self, method: str, *params: Any) -> None:
        ...

    @abstractmethod
    async def request(self, method: str, *params: Any) -> Sequence[Any]:
        ...

    @abstractmethod
    def on_callback(self, method: str, f: Callback) -> None:
        ...


class Api:
    _features: MutableMapping[str, bool] = {}

    def __init__(self, rpc: RPClient, prefix: str) -> None:
        self._rpc = rpc
        self.prefix = prefix

    def __getattr__(self, attr: str) -> CastReturnAF:
        method = f"{self._prefix}_{attr}"

        async def cont(ty: Type[_T], *params: Any) -> _T:
            resp = await self._rpc.request(method, *params)
            assert len(resp) == 1
            re, *_ = resp
            return cast(_T, re)

        return cont

    async def has(self, feature: str) -> bool:
        if (has := self._features.get(feature)) is not None:
            return has
        else:
            has, *_ = await self._rpc.request("nvim_call_function", "has", (feature,))
            self._features[feature] = has
            return has


class Fn:
    def __init__(self, api: Api) -> None:
        self._api = api

    def __getattr__(self, attr: str) -> CastReturnAF:
        async def cont(ty: Type[_T], *params: Any) -> _T:
            return await self._api.request(ty, "nvim_call_function", attr, params)

        return cont

    def __getitem__(self, attr: str) -> CastReturnAF:
        return self.__getattr__(attr)


class Vars:
    def __init__(self, api: Api) -> None:
        self._api = api

    async def has(self, key: str) -> bool:
        try:
            await self._api.get_var(NoneType, key)
        except Exception:
            return False
        else:
            return True

    async def get(self, ty: Type[_T], key: str) -> Optional[_T]:
        try:
            return await self._api.get_var(ty, key)
        except Exception:
            return None

    async def set(self, key: str, val: Any) -> None:
        await self._api.set_var(NoneType, key, val)

    async def delete(self, key: str) -> None:
        await self._api.del_var(NoneType, key)


class Opts:
    def __init__(self, api: Api) -> None:
        self._api = api

    async def get(self, ty: Type[_T], key: str) -> _T:
        return await self._api.get_option(ty, key)

    async def set(self, key: str, val: Any) -> None:
        await self._api.set_option(NoneType, key, val)


class HasAPI:
    prefix = ""
    api = cast(Api, None)

    @classmethod
    def init_api(cls, api: Api) -> None:
        cls.api = api


class HasChan:
    chan = cast(Chan, None)

    @classmethod
    def init_chan(cls, chan: Chan) -> None:
        cls.chan = chan


class Ext(HasAPI):
    code = cast(int, None)

    @classmethod
    def init_code(cls, code: int) -> None:
        assert isinstance(code, int)
        cls.code = code

    def __init__(self, data: bytes) -> None:
        self.data = data

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Ext):
            return self.code == other.code and self.data == other.data
        else:
            return False

    def __hash__(self) -> int:
        return hash((self.code, self.data))

    @cached_property
    def vars(self) -> Vars:
        return Vars(self.api)

    @cached_property
    def opts(self) -> Opts:
        return Opts(self.api)
