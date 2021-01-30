from dataclasses import dataclass
from itertools import repeat
from math import floor
from typing import Iterator, Optional
from uuid import uuid4

from pynvim import Nvim
from pynvim.api import Buffer, Window

from .api import (
    NvimPos,
    buf_set_lines,
    buf_set_var,
    create_buf,
    list_wins,
    win_get_var,
    win_set_option,
    win_set_var,
)

FLOATWIN_VAR_NAME = f"float_win_group_{uuid4().hex}"
FLOATWIN_BORDER_BUF_VAR_NAME = f"float_win_border_buf_{uuid4().hex}"


@dataclass(frozen=True)
class FloatWin:
    uid: str
    border_win: Window
    border_buf: Buffer
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
    win: Window = nvim.api.open_win(buf, True, opts)
    win_set_option(nvim, win=win, key="winhighlight", val="Normal:Floating")
    return win


def _border_buf(nvim: Nvim, width: int, height: int) -> Buffer:
    assert width >= 2
    assert height >= 2

    top = "╭" + ("─" * (width - 2)) + "╮"
    mid = "│" + ("#" * (width - 2)) + "│"
    btm = "╰" + ("─" * (width - 2)) + "╯"
    lines = tuple((top, *repeat(mid, times=height - 2), btm))

    buf = create_buf(
        nvim, listed=False, scratch=True, wipe=True, nofile=True, noswap=True
    )
    buf_set_var(nvim, buf=buf, key=FLOATWIN_BORDER_BUF_VAR_NAME, val=True)
    buf_set_lines(nvim, buf=buf, lo=0, hi=-1, lines=lines)
    return buf


def open_float_win(nvim: Nvim, margin: int, relsize: float, buf: Buffer) -> FloatWin:
    assert margin >= 0
    assert 0 < relsize < 1
    t_width, t_height = nvim.options["columns"], nvim.options["lines"]
    width = floor((t_width - margin) * relsize)
    height = floor((t_height - margin) * relsize)
    row, col = (t_height - height) / 2, (t_width - width) / 2

    border_buf = _border_buf(nvim, width=width, height=height)
    border_win = _open_float_win(
        nvim,
        buf=border_buf,
        width=width,
        height=height,
        pos=(row, col),
        focusable=False,
    )
    win = _open_float_win(
        nvim,
        buf=buf,
        width=width - 2,
        height=height - 2,
        pos=(row + 1, col + 1),
        focusable=True,
    )

    uid = uuid4().hex
    win_set_var(nvim, win=border_win, key=FLOATWIN_VAR_NAME, val=uid)
    win_set_var(nvim, win=win, key=FLOATWIN_VAR_NAME, val=uid)
    buf_set_var(nvim, buf=border_buf, key=FLOATWIN_VAR_NAME, val=uid)
    buf_set_var(nvim, buf=buf, key=FLOATWIN_VAR_NAME, val=uid)

    return FloatWin(
        uid=uid, border_win=border_win, border_buf=border_buf, win=win, buf=buf
    )
