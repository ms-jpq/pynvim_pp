from os import linesep
from string import whitespace
from typing import Iterable, Literal, Mapping, Tuple, TypeVar, Union

from pynvim import Nvim
from pynvim.api import Buffer

from .api import buf_get_lines, buf_get_mark, buf_get_option, buf_set_mark, str_col_pos

T = TypeVar("T")

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
    return (row1, col1), (row2, col2 + 1)


def set_visual_selection(
    nvim: Nvim, buf: Buffer, mark1: Tuple[int, int], mark2: Tuple[int, int]
) -> None:
    (row1, col1), (row2, col2) = mark1, mark2
    buf_set_mark(nvim, buf=buf, mark="<", row=row1, col=col1)
    buf_set_mark(nvim, buf=buf, mark=">", row=row2, col=col2)


def get_selected(nvim: Nvim, buf: Buffer, visual_type: VisualTypes) -> str:
    (row1, c1), (row2, c2) = operator_marks(nvim, buf=buf, visual_type=visual_type)
    lines = buf_get_lines(nvim, buf=buf, lo=row1, hi=row2 + 1)

    col1 = str_col_pos(nvim, buf=buf, row=row1, col=c1)
    col2 = str_col_pos(nvim, buf=buf, row=row2, col=c2) + 1

    if len(lines) == 1:
        return lines[0][col1:col2]
    else:
        head = lines[0][col1:]
        body = lines[1:-1]
        tail = lines[-1][:col2]
        return linesep.join((head, *body, tail))


def p_indent(line: str, tabsize: int) -> int:
    ws = {*whitespace}
    for idx, char in enumerate(line.expandtabs(tabsize), start=1):
        if char not in ws:
            return idx - 1
    else:
        return 0


def escape(stream: Iterable[T], escape: Mapping[T, T]) -> Iterable[T]:
    for unit in stream:
        if unit in escape:
            yield escape[unit]
        else:
            yield unit
