from __future__ import annotations

from dataclasses import dataclass
from inspect import currentframe
from typing import Callable, MutableMapping, Optional, Sequence
from uuid import uuid4

from .atomic import Atomic


def _name_gen() -> str:
    cf = currentframe()
    pf = cf.f_back if cf else None
    gf = pf.f_back if pf else None
    parent_mod = str(gf.f_globals.get("__name__", "")) if gf else ""
    mod = parent_mod or uuid4().hex
    qualname = f"{mod}_{uuid4().hex}"
    return qualname


@dataclass(frozen=True)
class _AuParams:
    events: Sequence[str]
    modifiers: Sequence[str]
    rhs: str


class _A:
    def __init__(
        self,
        name: str,
        events: Sequence[str],
        modifiers: Sequence[str],
        parent: AutoCMD,
    ) -> None:
        self._name, self._events, self._modifiers = name, events, modifiers
        self._parent = parent

    def __lshift__(self, rhs: str) -> None:
        self._parent._autocmds[self._name] = _AuParams(
            events=self._events, modifiers=self._modifiers, rhs=rhs
        )


class AutoCMD:
    def __init__(self, name_gen: Callable[[], str] = _name_gen) -> None:
        self._autocmds: MutableMapping[str, _AuParams] = {}
        self._name_gen = name_gen

    def __call__(
        self,
        event: str,
        *events: str,
        name: Optional[str] = None,
        modifiers: Sequence[str] = ("*",),
    ) -> _A:
        c_name = name or self._name_gen()
        return _A(
            name=c_name, events=(event, *events), modifiers=modifiers, parent=self
        )

    def drain(self) -> Atomic:
        atomic = Atomic()
        while self._autocmds:
            name, param = self._autocmds.popitem()
            events = ",".join(param.events)
            modifiers = " ".join(param.modifiers)
            atomic.command(f"augroup {name}")
            atomic.command("autocmd!")
            atomic.command(f"autocmd {events} {modifiers} {param.rhs}")
            atomic.command("augroup END")

        return atomic
