from enum import Enum
from typing import (
    Any,
    Iterator,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

from msgpack import packb
from pynvim.api import Buffer, Nvim, Tabpage, Window
from pynvim.api.common import NvimError

NvimPos = Tuple[int, int]


def new_buf(nvim: Nvim, nr: int) -> Buffer:
    ext_id = nvim.metadata["types"]["Buffer"]["id"]
    buf = Buffer(nvim, (ext_id, packb(nr)))
    return buf


def get_cwd(nvim: Nvim) -> str:
    cwd: str = nvim.funcs.getcwd()
    return cwd


def get_option(nvim: Nvim, key: str) -> Any:
    val = nvim.api.get_option(key)
    return val


def set_option(nvim: Nvim, key: str, val: Union[str, int, bool]) -> None:
    nvim.api.set_option(key, val)


def cur_tab(nvim: Nvim) -> Tabpage:
    tab: Tabpage = nvim.api.get_current_tabpage()
    return tab


def cur_win(nvim: Nvim) -> Window:
    win: Window = nvim.api.get_current_win()
    return win


def set_cur_win(nvim: Nvim, win: Window) -> None:
    nvim.api.set_current_win(win)


def cur_buf(nvim: Nvim) -> Buffer:
    buf: Buffer = nvim.api.get_current_buf()
    return buf


def list_tabs(nvim: Nvim) -> Sequence[Tabpage]:
    tabs: Sequence[Tabpage] = nvim.api.list_tabpages()
    return tabs


def list_wins(nvim: Nvim) -> Sequence[Window]:
    wins: Sequence[Window] = nvim.api.list_wins()
    return wins


def list_bufs(nvim: Nvim, listed: bool) -> Sequence[Buffer]:
    if listed:

        def parse(line: str) -> Iterator[str]:
            for char in line.lstrip():
                if char.isdigit():
                    yield char
                else:
                    break

        def cont() -> Iterator[Buffer]:
            raw: str = nvim.funcs.execute((":buffers",))
            for line in raw.strip().splitlines():
                num = "".join(parse(line))
                yield new_buf(nvim, nr=int(num))

        return tuple(cont())
    else:
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


def win_get_option(nvim: Nvim, win: Window, key: str) -> Any:
    opt = nvim.api.win_get_option(win, key)
    return opt


def win_set_option(
    nvim: Nvim, win: Window, key: str, val: Union[str, int, bool]
) -> None:
    nvim.api.win_set_option(win, key, val)


def buf_get_option(nvim: Nvim, buf: Buffer, key: str) -> Any:
    opt = nvim.api.buf_get_option(buf, key)
    return opt


def buf_set_option(
    nvim: Nvim, buf: Buffer, key: str, val: Union[str, int, bool]
) -> None:
    nvim.api.buf_set_option(buf, key, val)


def win_get_var(nvim: Nvim, win: Window, key: str) -> Optional[Any]:
    try:
        opt = nvim.api.win_get_var(win, key)
    except NvimError:
        return None
    else:
        return opt


def win_set_var(nvim: Nvim, win: Window, key: str, val: Any) -> None:
    nvim.api.win_set_var(win, key, val)


def buf_get_var(nvim: Nvim, buf: Buffer, key: str) -> Optional[Any]:
    try:
        opt = nvim.api.buf_get_var(buf, key)
    except NvimError:
        return None
    else:
        return opt


def buf_set_var(nvim: Nvim, buf: Buffer, key: str, val: Any) -> None:
    nvim.api.buf_set_var(buf, key, val)


def win_close(nvim: Nvim, win: Window) -> None:
    nvim.api.win_close(win, True)


def buf_close(nvim: Nvim, buf: Buffer) -> None:
    # nvim.api.buf_delete(buf, {"force": True})
    nvim.command(f"bwipeout! {buf.number}")


def win_get_cursor(nvim: Nvim, win: Window) -> NvimPos:
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


def buf_name(nvim: Nvim, buf: Buffer) -> str:
    name: str = nvim.api.buf_get_name(buf)
    return name


def buf_filetype(nvim: Nvim, buf: Buffer) -> str:
    filetype: str = buf_get_option(nvim, buf=buf, key="filetype")
    return filetype


class LFfmt(Enum):
    dos = "\r\n"
    unix = "\n"
    mac = "\r"


def buf_linefeed(nvim: Nvim, buf: Buffer) -> Literal["\r\n", "\n", "\r"]:
    lf: Literal["dos", "unix", "mac"] = buf_get_option(nvim, buf=buf, key="fileformat")
    return cast(Literal["\r\n", "\n", "\r"], LFfmt[lf].value)


def buf_get_lines(nvim: Nvim, buf: Buffer, lo: int, hi: int) -> Sequence[str]:
    lines: Sequence[str] = nvim.api.buf_get_lines(buf, lo, hi, True)
    return lines


def buf_set_lines(
    nvim: Nvim, buf: Buffer, lo: int, hi: int, lines: Sequence[str]
) -> None:
    nvim.api.buf_set_lines(buf, lo, hi, True, lines)


def buf_get_mark(nvim: Nvim, buf: Buffer, mark: str) -> NvimPos:
    row, col = nvim.api.buf_get_mark(buf, mark)
    return row - 1, col


def buf_set_mark(nvim: Nvim, buf: Buffer, mark: str, row: int, col: int) -> None:
    marked = "'" + mark
    nvim.funcs.setpos(marked, (buf.number, row + 1, col + 1, 0))


def create_buf(
    nvim: Nvim, listed: bool, scratch: bool, wipe: bool, nofile: bool, noswap: bool
) -> Buffer:
    buf: Buffer = nvim.api.create_buf(listed, scratch)
    if wipe:
        buf_set_option(nvim, buf=buf, key="bufhidden", val="wipe")
    if nofile:
        buf_set_option(nvim, buf=buf, key="buftype", val="nofile")
    if noswap:
        buf_set_option(nvim, buf=buf, key="swapfile", val=False)
    return buf


def ask_mc(
    nvim: Nvim, question: str, answers: str, answer_key: Mapping[int, Any]
) -> Optional[Any]:
    try:
        resp: Optional[int] = nvim.funcs.confirm(question, answers, 0)
    except NvimError:
        resp = None
    if resp is None:
        return None
    else:
        return answer_key.get(resp)


def ask(nvim: Nvim, question: str, default: str) -> Optional[str]:
    try:
        resp: Optional[str] = nvim.funcs.input(question, default)
    except NvimError:
        return None
    else:
        return resp

