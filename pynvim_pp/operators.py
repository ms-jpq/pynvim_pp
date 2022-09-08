from string import whitespace
from typing import Literal, Optional, Tuple, cast

from .atomic import Atomic
from .buffer import Buffer
from .types import NoneType, NvimPos
from .window import Window

VisualMode = Literal["v", "V"]
VisualTypes = Optional[Literal["char", "line", "block"]]


async def operator_marks(
    buf: Buffer, visual_type: VisualTypes
) -> Tuple[NvimPos, NvimPos]:
    assert visual_type in {None, "char", "line", "block"}
    mark1, mark2 = ("[", "]") if visual_type else ("<", ">")
    with Atomic() as (atomic, ns):
        ns.m1 = atomic.buf_get_mark(buf, mark1)
        ns.m2 = atomic.buf_get_mark(buf, mark2)

        await atomic.commit(NoneType)
    (row1, col1) = cast(NvimPos, ns.m1(NoneType))
    (row2, col2) = cast(NvimPos, ns.m2(NoneType))
    return (row1 - 1, col1), (row2 - 1, col2 + 1)


async def set_visual_selection(
    win: Window,
    mode: VisualMode,
    mark1: NvimPos,
    mark2: NvimPos,
    reverse: bool = False,
) -> None:
    assert mode in {"v", "V"}
    (r1, c1), (r2, c2) = mark1, mark2
    atomic = Atomic()
    if reverse:
        atomic.win_set_cursor(win, (r2 + 1, max(0, c2 - 1)))
        atomic.command(f"norm! {mode}")
        atomic.win_set_cursor(win, (r1 + 1, c1))

    else:
        atomic.win_set_cursor(win, (r1 + 1, c1))
        atomic.command(f"norm! {mode}")
        atomic.win_set_cursor(win, (r2 + 1, max(0, c2 - 1)))
    await atomic.commit(NoneType)


def p_indent(line: str, tabsize: int) -> int:
    ws = {*whitespace}
    spaces = " " * tabsize
    for idx, char in enumerate(line.replace("\t", spaces), start=1):
        if char not in ws:
            return idx - 1
    else:
        return 0
