from string import whitespace
from typing import Literal, Optional, Tuple

from pynvim import Nvim
from pynvim.api import Buffer, Window

from .api import NvimPos, buf_get_mark, buf_get_option, win_set_cursor

VisualMode = Literal["v", "V"]
VisualTypes = Optional[Literal["char", "line", "block"]]


def writable(nvim: Nvim, buf: Buffer) -> bool:
    is_modifiable: bool = buf_get_option(nvim, buf=buf, key="modifiable")
    return is_modifiable


def operator_marks(
    nvim: Nvim, buf: Buffer, visual_type: VisualTypes
) -> Tuple[NvimPos, NvimPos]:
    mark1, mark2 = ("[", "]") if visual_type else ("<", ">")
    row1, col1 = buf_get_mark(nvim, buf=buf, mark=mark1)
    row2, col2 = buf_get_mark(nvim, buf=buf, mark=mark2)
    return (row1, col1), (row2, col2)


def set_visual_selection(
    nvim: Nvim, win: Window, mode: VisualMode, mark1: NvimPos, mark2: NvimPos
) -> None:
    (r1, c1), (r2, c2) = mark1, mark2
    win_set_cursor(nvim, win=win, row=r1, col=c1)
    nvim.command(f"norm! {mode}")
    win_set_cursor(nvim, win=win, row=r2, col=c2)


def p_indent(line: str, tabsize: int) -> int:
    ws = {*whitespace}
    for idx, char in enumerate(line.expandtabs(tabsize), start=1):
        if char not in ws:
            return idx - 1
    else:
        return 0
