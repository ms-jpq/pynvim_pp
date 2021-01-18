from string import whitespace
from typing import Literal, Tuple, Union

from pynvim import Nvim
from pynvim.api import Buffer

from .api import buf_get_mark, buf_get_option, buf_set_mark

VisualTypes = Union[Literal["char"], Literal["line"], Literal["block"], None]


def writable(nvim: Nvim, buf: Buffer) -> bool:
    is_modifiable: bool = buf_get_option(nvim, buf=buf, key="modifiable")
    return is_modifiable


def operator_marks(
    nvim: Nvim, buf: Buffer, visual_type: VisualTypes
) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    mark1, mark2 = ("[", "]") if visual_type else ("<", ">")
    row1, col1 = buf_get_mark(nvim, buf=buf, mark=mark1)
    row2, col2 = buf_get_mark(nvim, buf=buf, mark=mark2)
    return (row1, col1), (row2, col2)


def set_visual_selection(
    nvim: Nvim, buf: Buffer, mark1: Tuple[int, int], mark2: Tuple[int, int]
) -> None:
    (row1, col1), (row2, col2) = mark1, mark2
    buf_set_mark(nvim, buf=buf, mark="<", row=row1, col=col1)
    buf_set_mark(nvim, buf=buf, mark=">", row=row2, col=col2)


def p_indent(line: str, tabsize: int) -> int:
    ws = {*whitespace}
    for idx, char in enumerate(line.expandtabs(tabsize), start=1):
        if char not in ws:
            return idx - 1
    else:
        return 0
