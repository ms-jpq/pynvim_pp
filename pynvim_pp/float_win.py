from dataclasses import dataclass
from math import floor
from typing import Iterator, Optional, Union, Sequence, Tuple
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


def get_border_size(
    border: Union[str, Sequence[Union[str, Sequence[str]]]],
) -> Tuple[int, int]:
    if isinstance(border, str):
        return {
            "none": (0, 0),
            "shadow": (1, 1),
        }.get(border, (2, 2))
    else:

        def border_size(id: int) -> int:
            id = id % len(border)
            if isinstance(border[id], str):
                return 1 if border[id] else 0
            else:
                return 1 if border[id][0] else 0

        # (height, width)
        return (border_size(1) + border_size(5), border_size(3) + border_size(7))


def _open_float_win(
    nvim: Nvim,
    buf: Buffer,
    width: int,
    height: int,
    pos: NvimPos,
    focusable: bool,
    border: Union[str, Sequence[Union[str, Sequence[str]]]],
) -> Window:
    row, col = pos
    opts = {
        "relative": "editor",
        "anchor": "NW",
        "style": "minimal",
        "noautocmd": True,
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
    nvim: Nvim,
    margin: int,
    relsize: float,
    buf: Buffer,
    border: Union[str, Sequence[Union[str, Sequence[str]]]],
) -> FloatWin:
    assert margin >= 0
    assert 0 < relsize < 1
    t_width, t_height = nvim.options["columns"], nvim.options["lines"]
    width = floor((t_width - margin) * relsize)
    height = floor((t_height - margin) * relsize)
    border_height, border_width = get_border_size(border)
    row = (t_height - height - border_height) / 2
    col = (t_width - width - border_width) / 2

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
