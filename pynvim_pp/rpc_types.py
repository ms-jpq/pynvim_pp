from __future__ import annotations

from abc import abstractmethod
from enum import Enum, unique
from ipaddress import IPv4Address, IPv6Address
from pathlib import PurePath
from typing import Any, Literal, NewType, Protocol, Tuple, TypeVar, Union, cast
from uuid import UUID

_T_co = TypeVar("_T_co", covariant=True)

ExtData = NewType("ExtData", bytes)
Chan = NewType("Chan", int)
Method = NewType("Method", str)

ServerAddr = Union[
    PurePath, Tuple[Union[Literal["localhost"], IPv4Address, IPv6Address], int]
]


class NvimError(Exception):
    ...


@unique
class MsgType(Enum):
    req = 0
    resp = 1
    notif = 2


class MsgPackExt:
    code = cast(int, None)

    @classmethod
    def init_code(cls, code: int) -> None:
        assert isinstance(code, int)
        cls.code = code

    def __init__(self, data: ExtData) -> None:
        self.data = ExtData(data)

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, MsgPackExt)
            and self.code == other.code
            and self.data == other.data
        )

    def __hash__(self) -> int:
        return hash((self.code, self.data))


class MsgPackTabpage(MsgPackExt):
    ...


class MsgPackWindow(MsgPackExt):
    ...


class MsgPackBuffer(MsgPackExt):
    ...


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
    def method(self) -> Method:
        ...

    async def __call__(self, *args: Any, **kwargs: Any) -> _T_co:
        ...


class RPClient(Protocol):
    @property
    @abstractmethod
    def chan(self) -> Chan:
        ...

    @abstractmethod
    async def notify(self, method: Method, *params: Any) -> None:
        ...

    @abstractmethod
    async def request(self, method: Method, *params: Any) -> Any:
        ...

    @abstractmethod
    def register(self, f: RPCallable) -> None:
        ...
