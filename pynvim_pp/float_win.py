from dataclasses import dataclass
from math import floor
from typing import AsyncIterator, Literal, Tuple, Union
from uuid import uuid4

from .atomic import Atomic
from .buffer import Buffer
from .lib import display_width
from .nvim import Nvim
from .types import NoneType, NvimPos
from .window import Window

FLOATWIN_VAR_NAME = f"float_win_group_{uuid4().hex}"


@dataclass(frozen=True)
class FloatWin:
    uid: str
    win: Window
    buf: Buffer


Border = Union[
    None,
    Literal["single", "double", "rounded", "solid", "shadow"],
    Tuple[str, str, str, str, str, str, str, str],
    Tuple[
        Tuple[str, str],
        Tuple[str, str],
        Tuple[str, str],
        Tuple[str, str],
        Tuple[str, str],
        Tuple[str, str],
        Tuple[str, str],
        Tuple[str, str],
    ],
]


async def list_floatwins() -> AsyncIterator[Window]:
    for win in await Window.list():
        if await win.vars.has(FLOATWIN_VAR_NAME):
            yield win


def border_w_h(
    border: Border,
) -> Tuple[int, int]:
    if not border:
        return (0, 0)
    elif isinstance(border, str):
        return (1, 1) if border == "shadow" else (2, 2)
    else:

        def size(spec: Union[str, Tuple[str, str]]) -> int:
            if isinstance(spec, str):
                char = spec
            else:
                char, _ = spec
            length = display_width(char, tabsize=16)
            assert length in {0, 1}
            return length

        width = size(border[7]) + size(border[3])
        height = size(border[1]) + size(border[5])
        return width, height


async def _open_float_win(
    buf: Buffer,
    width: int,
    height: int,
    pos: NvimPos,
    focusable: bool,
    border: Border,
) -> Window:
    row, col = pos
    opts = {
        "relative": "editor",
        "anchor": "NW",
        "style": "minimal",
        "width": width,
        "height": height,
        "row": row,
        "col": col,
        "focusable": focusable,
    }
    if buf.api.has("nvim-0.5"):
        opts.update(noautocmd=True, border=border)

    win = await buf.api.open_win(Window, buf, True, opts)
    await win.opts.set("winhighlight", "Normal:Floating")
    return win


async def open_float_win(
    margin: int,
    relsize: float,
    buf: Buffer,
    border: Border,
) -> FloatWin:
    assert margin >= 0
    assert 0 < relsize < 1
    if not await buf.api.has("nvim-0.5"):
        border = None

    t_height, t_width = await Nvim.size()
    width = floor((t_width - margin) * relsize)
    height = floor((t_height - margin) * relsize)
    b_width, b_height = border_w_h(border)
    row = (t_height - height) // 2 + 1
    col = (t_width - width) // 2 + 1

    win = await _open_float_win(
        buf,
        width=width - b_width,
        height=height - b_height,
        pos=(row, col),
        focusable=True,
        border=border,
    )

    uid = uuid4().hex
    atomic = Atomic()

    atomic.win_set_var(buf, FLOATWIN_VAR_NAME, uid)
    atomic.buf_set_var(buf, FLOATWIN_VAR_NAME, uid)
    await atomic.commit(NoneType)

    return FloatWin(uid=uid, win=win, buf=buf)
