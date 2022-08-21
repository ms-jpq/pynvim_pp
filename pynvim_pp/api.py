from contextlib import suppress
from dataclasses import dataclass
from enum import Enum
from os.path import normcase
from pathlib import Path, PurePath
from string import ascii_lowercase, ascii_uppercase
from typing import (
    Any,
    Iterable,
    Iterator,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

from msgpack import packb
from pynvim.api import Buffer, Nvim, Tabpage, Window
from pynvim.api.common import NvimError

from .lib import decode, encode, nvim_has, resolve_path

NvimPos = Tuple[int, int]

_T = TypeVar("_T")


@dataclass(frozen=True)
class ExtMarkBase:
    idx: int
    begin: NvimPos
    meta: Mapping[str, Any]


@dataclass(frozen=True)
class ExtMark(ExtMarkBase):
    end: NvimPos


@dataclass(frozen=True)
class Bookmark:
    name: str
    row: int
    col: int


def new_buf(nvim: Nvim, nr: int) -> Buffer:
    ext_id = nvim.metadata["types"]["Buffer"]["id"]
    buf = Buffer(nvim, (ext_id, packb(nr)))
    return buf


def get_cwd(nvim: Nvim) -> Path:
    cwd = normcase(nvim.funcs.getcwd())
    return Path(cwd)


def chdir(nvim: Nvim, path: PurePath, history: bool = True) -> None:
    if history:
        escaped = nvim.funcs.fnameescape(normcase(path))
        nvim.command(f"chdir {escaped}")
    else:
        nvim.api.set_current_dir(normcase(path))


def iter_rtps(nvim: Nvim) -> Sequence[Path]:
    return tuple(
        path
        for p in nvim.api.list_runtime_paths()
        if (path := resolve_path(None, path=p))
    )


def get_option(nvim: Nvim, key: str) -> Any:
    val = nvim.api.get_option(key)
    return val


def set_option(nvim: Nvim, key: str, val: Union[str, int, bool]) -> None:
    nvim.api.set_option(key, val)


def create_ns(nvim: Nvim, ns: UUID) -> int:
    id: int = nvim.api.create_namespace(ns.hex)
    return id


def clear_ns(nvim: Nvim, buf: Buffer, id: int, lo: int = 0, hi: int = -1) -> None:
    nvim.api.buf_clear_namespace(buf, id, lo, hi)


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


def list_bookmarks(nvim: Nvim) -> Iterator[Tuple[str, PurePath]]:
    if nvim_has(nvim, "nvim-0.6"):
        cwd = get_cwd(nvim)
        for mark_id in ascii_uppercase:
            _, _, _, path = nvim.api.get_mark(mark_id, {})
            if path and (resolved := resolve_path(cwd, path=path)):
                yield mark_id, resolved


def list_local_bookmarks(nvim: Nvim) -> Mapping[Buffer, Bookmark]:
    def cont() -> Iterator[Tuple[Buffer, Bookmark]]:
        if nvim_has(nvim, "nvim-0.6"):
            for mark_id in ascii_lowercase:
                row, col, buf, _ = nvim.api.get_mark(mark_id, {})
                bookmark = Bookmark(name=mark_id, row=row, col=col)
                yield buf, bookmark

    return {b: m for b, m in cont()}


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


def _buf_get_ext_marks(
    nvim: Nvim, buf: Buffer, id: int
) -> Sequence[Tuple[int, int, int, Mapping[str, Any]]]:
    marks: Sequence[
        Tuple[int, int, int, Mapping[str, Any]]
    ] = nvim.api.buf_get_extmarks(buf, id, 0, -1, {"details": True})
    return marks


def buf_get_extmarks_base(nvim: Nvim, buf: Buffer, id: int) -> Iterator[ExtMarkBase]:
    for idx, r1, c1, details in _buf_get_ext_marks(nvim, buf=buf, id=id):
        mark = ExtMarkBase(
            idx=idx,
            begin=(r1, c1),
            meta=details,
        )
        yield mark


def buf_get_extmarks(nvim: Nvim, buf: Buffer, id: int) -> Iterator[ExtMark]:
    for idx, r1, c1, details in _buf_get_ext_marks(nvim, buf=buf, id=id):
        mark = ExtMark(
            idx=idx,
            begin=(r1, c1),
            end=(details["end_row"], details["end_col"]),
            meta=details,
        )
        yield mark


def buf_set_extmarks_base(
    nvim: Nvim, buf: Buffer, id: int, marks: Iterable[ExtMarkBase]
) -> None:
    for mark in marks:
        (r1, c1) = mark.begin
        opts: Mapping[str, Union[str, int]] = {**mark.meta, "id": mark.idx}
        nvim.api.buf_set_extmark(buf, id, r1, c1, opts)


def buf_set_extmarks(
    nvim: Nvim, buf: Buffer, id: int, marks: Iterable[ExtMark]
) -> None:
    for mark in marks:
        (r1, c1), (r2, c2) = mark.begin, mark.end
        opts: Mapping[str, Union[str, int]] = {
            **mark.meta,
            "id": mark.idx,
            "end_line": r2,
            "end_col": c2,
        }
        nvim.api.buf_set_extmark(buf, id, r1, c1, opts)


def buf_del_extmarks(
    nvim: Nvim, buf: Buffer, id: int, marks: Iterable[ExtMarkBase]
) -> None:
    for mark in marks:
        nvim.api.buf_del_extmark(buf, id, mark.idx)


def win_close(nvim: Nvim, win: Window) -> None:
    nvim.api.win_close(win, True)


def buf_close(nvim: Nvim, buf: Buffer) -> None:
    if nvim_has(nvim, "nvim-0.5"):
        nvim.api.buf_delete(buf, {"force": True})
    else:
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


def buf_commentstr(nvim: Nvim, buf: Buffer) -> Tuple[str, str]:
    commentstr: Optional[str] = buf_get_option(nvim, buf=buf, key="commentstring")
    if not commentstr:
        return "", ""
    else:
        lhs, sep, rhs = commentstr.partition("%s")
        assert sep
        return lhs, rhs


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


def buf_get_text(
    nvim: Nvim, buf: Buffer, begin: NvimPos, end: NvimPos
) -> Sequence[str]:
    (r1, c1), (r2, c2) = begin, end
    if nvim_has(nvim, "nvim-0.7"):
        lines: Sequence[str] = nvim.api.buf_get_text(buf, r1, c1, r2, c2, {})
        return lines
    else:
        c2 = max(0, c2 - 1)
        lo, hi = min(r1, r2), max(r1, r2) + 1
        lines = buf_get_lines(nvim, buf=buf, lo=lo, hi=hi)

        def cont() -> Iterator[str]:
            for idx, line in enumerate(lines, start=lo):
                if idx == r1 and idx == r2:
                    yield decode(encode(line)[c1:c2])
                elif idx == r1:
                    yield decode(encode(line)[c1:])
                elif idx == r2:
                    yield decode(encode(line)[:c2])
                else:
                    yield line

        return tuple(cont())


def buf_set_text(
    nvim: Nvim, buf: Buffer, begin: NvimPos, end: NvimPos, text: Sequence[str]
) -> None:
    (r1, c1), (r2, c2) = begin, end
    nvim.api.buf_set_text(buf, r1, c1, r2, c2, text)


def extmarks_text(
    nvim: Nvim, buf: Buffer, marks: Iterable[ExtMark]
) -> Iterator[Tuple[ExtMark, str]]:
    linesep = buf_linefeed(nvim, buf=buf)
    for mark in marks:
        with suppress(NvimError):
            lines = buf_get_text(nvim, buf=buf, begin=mark.begin, end=mark.end)
            yield mark, linesep.join(lines)


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
    nvim: Nvim, question: str, answers: str, answer_key: Mapping[int, _T]
) -> Optional[_T]:
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
