from typing import Optional, Sequence, Tuple, TypeVar, Union

from pynvim.api import Buffer, Nvim, Tabpage, Window
from pynvim.api.common import NvimError

T = TypeVar("T")


def current_tab(nvim: Nvim) -> Tabpage:
    tab: Tabpage = nvim.api.get_current_tabpage()
    return tab


def cur_window(nvim: Nvim) -> Window:
    win: Window = nvim.api.get_current_win()
    return win


def set_cur_window(nvim: Nvim, win: Window) -> None:
    nvim.api.set_current_win(win)


def cur_buf(nvim: Nvim) -> Buffer:
    buf: Buffer = nvim.api.get_current_buf()
    return buf


def list_tabs(nvim: Nvim) -> Sequence[Tabpage]:
    tabs: Sequence[Tabpage] = nvim.api.list_tabpages()
    return tabs


def list_win(nvim: Nvim) -> Sequence[Window]:
    wins: Sequence[Window] = nvim.api.list_wins()
    return wins


def list_bufs(nvim: Nvim) -> Sequence[Buffer]:
    bufs: Sequence[Buffer] = nvim.api.list_bufs()
    return bufs


def tab_list_wins(nvim: Nvim, tab: Tabpage) -> Sequence[Window]:
    wins: Sequence[Window] = nvim.api.tabpage_list_wins(tab)
    return wins


def win_get_buf(nvim: Nvim, win: Window) -> Buffer:
    buf: Buffer = nvim.api.win_get_buf(win)
    return buf


def win_set_buf(nvim: Nvim, win: Window, buf: Buffer) -> None:
    nvim.api.win_set_buf(win, buf)


def win_get_option(nvim: Nvim, win: Window, key: str) -> T:
    opt: T = nvim.api.win_get_option(win, key)
    return opt


def win_set_option(
    nvim: Nvim, win: Window, key: str, val: Union[str, int, bool]
) -> None:
    nvim.api.win_set_option(win, key, val)


def buf_get_option(nvim: Nvim, buf: Buffer, key: str) -> T:
    opt: T = nvim.api.buf_get_option(buf, key)
    return opt


def buf_set_option(
    nvim: Nvim, buf: Buffer, key: str, val: Union[str, int, bool]
) -> None:
    nvim.api.buf_set_option(buf, key, val)


def win_get_var(nvim: Nvim, win: Window, key: str) -> Optional[T]:
    try:
        opt: T = nvim.api.win_get_var(win, key)
    except NvimError:
        return None
    else:
        return opt


def win_set_var(nvim: Nvim, win: Window, key: str, val: Union[str, int, bool]) -> None:
    nvim.api.win_set_var(win, key, val)


def buf_get_var(nvim: Nvim, buf: Buffer, key: str) -> Optional[T]:
    try:
        opt: T = nvim.api.buf_get_var(buf, key)
    except NvimError:
        return None
    else:
        return opt


def buf_set_var(nvim: Nvim, buf: Buffer, key: str, val: Union[str, int, bool]) -> None:
    nvim.api.buf_set_var(buf, key, val)


def win_get_cursor(nvim: Nvim, win: Window) -> Tuple[int, int]:
    """
    col is byte indexed
    """

    row, col = nvim.api.win_get_cursor(win)
    return row - 1, col


def win_set_cursor(nvim: Nvim, win: Window, row: int, col: int) -> None:
    """
    col is byte indexed
    """

    nvim.api.win_set_cursor(win, (row + 1, col))


def buf_line_count(nvim: Nvim, buf: Buffer) -> int:
    count: int = nvim.api.buf_line_count(buf)
    return count


def buf_get_lines(nvim: Nvim, buf: Buffer, lo: int, hi: int) -> Sequence[str]:
    lines: Sequence[str] = nvim.api.buf_get_lines(buf, lo, hi, True)
    return lines


def buf_set_lines(
    nvim: Nvim, buf: Buffer, lo: int, hi: int, lines: Sequence[str]
) -> None:
    nvim.api.buf_set_lines(buf, lo, hi, True, lines)


def buf_get_mark(nvim: Nvim, buf: Buffer, mark: str) -> Tuple[int, int]:
    row, col = nvim.api.buf_get_mark(buf, mark)
    return row - 1, col


def buf_set_mark(nvim: Nvim, buf: Buffer, mark: str, row: int, col: int) -> None:
    marked = "'" + mark
    nvim.funcs.setpos(marked, (buf.number, row + 1, col + 1, 0))


def create_buf(
    nvim: Nvim, listed: bool, scratch: bool, wipe: bool, nofile: bool
) -> Buffer:
    buf: Buffer = nvim.api.create_buf(listed, scratch)
    if wipe:
        buf_set_option(nvim, buf=buf, key="bufhidden", val="wipe")
    if nofile:
        buf_set_option(nvim, buf=buf, key="buftype", val="nofile")
    return buf


def str_col_pos(nvim: Nvim, buf: Buffer, row: int, col: int) -> int:
    """
    byte indexed col -> utf-8 encoded col
    """

    lines: Sequence[str] = nvim.api.buf_get_lines(buf, row - 1, row, True)
    line = next(iter(lines))
    parted = nvim.funcs.strpart(line, 0, col)
    return len(parted)
