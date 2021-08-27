from dataclasses import dataclass
from math import floor
from typing import Iterator, Literal, Optional, Tuple, Union
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
from .lib import display_width

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


def list_floatwins(nvim: Nvim) -> Iterator[Window]:
    for win in list_wins(nvim):
        flag: Optional[str] = win_get_var(nvim, win, FLOATWIN_VAR_NAME)
        if flag:
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


def _open_float_win(
    nvim: Nvim,
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
    border: Border,
) -> FloatWin:
    assert margin >= 0
    assert 0 < relsize < 1
    t_width, t_height = nvim.options["columns"], nvim.options["lines"]
    width = floor((t_width - margin) * relsize)
    height = floor((t_height - margin) * relsize)
    b_width, b_height = border_w_h(border)
    row = (t_height - height) / 2 + 1
    col = (t_width - width) / 2 + 1

    win = _open_float_win(
        nvim,
        buf=buf,
        width=width - b_width,
        height=height - b_height,
        pos=(row, col),
        focusable=True,
        border=border,
    )

    uid = uuid4().hex
    win_set_var(nvim, win=win, key=FLOATWIN_VAR_NAME, val=uid)
    buf_set_var(nvim, buf=buf, key=FLOATWIN_VAR_NAME, val=uid)

    return FloatWin(uid=uid, win=win, buf=buf)
