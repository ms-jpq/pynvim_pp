from dataclasses import dataclass
from math import floor
from typing import Iterator, Optional
from uuid import uuid4

from pynvim import Nvim
from pynvim.api import Buffer, Window

from .api import (
    NvimPos,
    buf_set_var,
    list_wins,
    win_get_var,
    win_set_option,
    win_set_var,
)

FLOATWIN_VAR_NAME = f"float_win_group_{uuid4().hex}"


@dataclass(frozen=True)
class FloatWin:
    uid: str
    win: Window
    buf: Buffer


def list_floatwins(nvim: Nvim) -> Iterator[Window]:
    for win in list_wins(nvim):
        flag: Optional[str] = win_get_var(nvim, win, FLOATWIN_VAR_NAME)
        if flag:
            yield win


def _open_float_win(
    nvim: Nvim,
    buf: Buffer,
    width: int,
    height: int,
    pos: NvimPos,
    focusable: bool,
    border: str,
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
        "border": border,
    }
    win: Window = nvim.api.open_win(buf, True, opts)
    win_set_option(nvim, win=win, key="winhighlight", val="Normal:Floating")
    return win


def open_float_win(
    nvim: Nvim, margin: int, relsize: float, buf: Buffer, border: str
) -> FloatWin:
    assert margin >= 0
    assert 0 < relsize < 1
    t_width, t_height = nvim.options["columns"], nvim.options["lines"]
    width = floor((t_width - margin) * relsize)
    height = floor((t_height - margin) * relsize)
    row, col = (t_height - height) / 2, (t_width - width) / 2

    win = _open_float_win(
        nvim,
        buf=buf,
        width=width - 2,
        height=height - 2,
        pos=(row + 1, col + 1),
        focusable=True,
        border=border,
    )

    uid = uuid4().hex
    win_set_var(nvim, win=win, key=FLOATWIN_VAR_NAME, val=uid)
    buf_set_var(nvim, buf=buf, key=FLOATWIN_VAR_NAME, val=uid)

    return FloatWin(uid=uid, win=win, buf=buf)
