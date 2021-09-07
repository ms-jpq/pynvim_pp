from typing import Iterator, Optional, Sequence, Tuple

from pynvim import Nvim
from pynvim.api import Buffer, Tabpage, Window

from .api import (
    buf_set_lines,
    buf_set_option,
    cur_tab,
    cur_win,
    set_cur_win,
    tab_list_wins,
    win_get_buf,
    win_get_option,
    win_set_option,
)


def preview_windows_in_tab(
    nvim: Nvim, tab: Optional[Tabpage] = None
) -> Iterator[Window]:
    tab = tab or cur_tab(nvim)
    wins = tab_list_wins(nvim, tab=tab)
    for win in wins:
        opt: bool = win_get_option(nvim, win=win, key="previewwindow")
        if opt:
            yield win


def _open_preview(nvim: Nvim) -> Tuple[Window, Buffer]:
    win = next(preview_windows_in_tab(nvim), None)
    if win:
        set_cur_win(nvim, win=win)
        buf = win_get_buf(nvim, win=win)
        return win, buf
    else:
        nvim.api.command("new")
        win = cur_win(nvim)
        buf = win_get_buf(nvim, win=win)
        win_set_option(nvim, win=win, key="previewwindow", val=True)
        buf_set_option(nvim, buf=buf, key="bufhidden", val="wipe")
        height = nvim.options["previewheight"]
        nvim.api.win_set_height(win, height)
        return win, buf


def buf_set_preview(
    nvim: Nvim, buf: Buffer, syntax: str, preview: Sequence[str]
) -> None:
    buf_set_option(nvim, buf=buf, key="undolevel", val=-1)
    buf_set_option(nvim, buf=buf, key="buftype", val="nofile")
    buf_set_option(nvim, buf=buf, key="modifiable", val=True)
    buf_set_lines(nvim, buf=buf, lo=0, hi=-1, lines=preview)
    buf_set_option(nvim, buf=buf, key="modifiable", val=False)
    buf_set_option(nvim, buf=buf, key="syntax", val=syntax)


def set_preview(nvim: Nvim, syntax: str, preview: Sequence[str]) -> Buffer:
    _, buf = _open_preview(nvim)
    buf_set_preview(nvim, buf=buf, syntax=syntax, preview=preview)
    return buf

