from __future__ import annotations

from enum import Enum
from typing import Iterable, MutableMapping, MutableSequence, Sequence, Tuple, Union

from .atomic import Atomic


class _OP(Enum):
    exact = ""
    equals = "="
    plus = "+="
    minus = "-="


class _Setting:
    def __init__(self, name: str, parent: Settings) -> None:
        self.name, self._parent = name, parent

    def __iadd__(self, vals: Iterable[str]) -> _Setting:
        self._parent._conf.setdefault(self.name, []).append((_OP.plus, ",".join(vals)))
        return self

    def __isub__(self, vals: Iterable[str]) -> _Setting:
        self._parent._conf.setdefault(self.name, []).append((_OP.minus, ",".join(vals)))
        return self


class Settings:
    def __init__(self) -> None:
        self._conf: MutableMapping[str, MutableSequence[Tuple[_OP, str]]] = {}

    def __getitem__(self, key: str) -> _Setting:
        return _Setting(name=key, parent=self)

    def __setitem__(
        self, key: str, val: Union[_Setting, str, int, bool, Sequence[str]]
    ) -> None:
        if isinstance(val, _Setting):
            pass
        elif isinstance(val, bool):
            self._conf.setdefault(key, []).append((_OP.exact, ""))
        elif isinstance(val, int):
            self._conf.setdefault(key, []).append((_OP.equals, str(val)))
        elif isinstance(val, str):
            self._conf.setdefault(key, []).append((_OP.equals, val))
        elif isinstance(val, Sequence):
            self._conf.setdefault(key, []).append((_OP.equals, ",".join(val)))
        else:
            raise TypeError()

    def drain(self) -> Atomic:
        atomic = Atomic()
        while self._conf:
            key, values = self._conf.popitem()
            for op, val in values:
                atomic.command(f"set {key}{op.value}{val}")

        return atomic
