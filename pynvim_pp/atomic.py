from __future__ import annotations

from typing import (
    Any,
    Iterator,
    MutableMapping,
    MutableSequence,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    cast,
)

from .nvim import NvimError
from .types import Api, NoneType

_T = TypeVar("_T")


class _CastReturnF(Protocol):
    def __call__(self, ty: Type[_T]) -> _T:
        ...


_AtomicInstruction = Tuple[str, Sequence[Any]]


class _A:
    def __init__(self, name: str, parent: Atomic) -> None:
        self._name, self._parent = name, parent

    def __call__(self, *args: Any) -> _CastReturnF:
        self._parent._instructions.append((self._name, args))
        idx = len(self._parent._instructions) - 1
        return cast(_CastReturnF, idx)


class _NS:
    def __init__(self, parent: Atomic) -> None:
        self._parent = parent

    def __getattr__(self, name: str) -> _CastReturnF:
        if not self._parent._commited:
            raise RuntimeError()
        else:
            if name in self._parent._ns_mapping:
                val = self._parent._resultset[self._parent._ns_mapping[name]]

                def cont(ty: Type[_T]) -> _T:
                    return cast(_T, val)

                return cont
            else:
                raise AttributeError()

    def __setattr__(self, key: str, val: Any) -> None:
        assert isinstance(val, int)
        if key == "_parent":
            super().__setattr__(key, val)
        elif self._parent._commited:
            raise RuntimeError()
        else:
            self._parent._ns_mapping[key] = val


class Atomic:
    _api: Optional[Api] = None

    def __init__(self, prefix: str = "nvim") -> None:
        self._prefix = prefix
        self._commited = False
        self._instructions: MutableSequence[_AtomicInstruction] = []
        self._resultset: MutableSequence[Any] = []
        self._ns_mapping: MutableMapping[str, int] = {}

    def __enter__(self) -> Tuple[Atomic, _NS]:
        return self, _NS(parent=self)

    def __exit__(self, *_: Any) -> None:
        return None

    def __iter__(self) -> Iterator[_AtomicInstruction]:
        return iter(self._instructions)

    def __add__(self, other: Atomic) -> Atomic:
        new = Atomic()
        new._instructions.extend(self._instructions)
        new._instructions.extend(other._instructions)
        return new

    def __getattr__(self, name: str) -> _A:
        return _A(name=name, parent=self)

    async def commit(self, ty: Type[_T]) -> Sequence[_T]:
        if self._commited:
            raise RuntimeError()
        else:
            assert self._api

            self._commited = True
            inst = tuple(
                (f"{self._prefix}_{instruction}", args)
                for instruction, args in self._instructions
            )
            out, err = cast(
                Tuple[Sequence[Any], Sequence[Any]],
                await self._api.call_atomic(NoneType, inst),
            )
            if err:
                self._resultset[:] = []
                idx, _, err_msg = err
                raise NvimError((err_msg, self._instructions[idx]))
            else:
                self._resultset[:] = out
                return cast(Sequence[_T], out)
