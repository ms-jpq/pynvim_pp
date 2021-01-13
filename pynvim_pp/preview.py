from typing import Iterator, Optional

from pynvim import Nvim
from pynvim.api import Buffer, Tabpage, Window

from .api import (
    buf_set_lines,
    buf_set_option,
    cur_window,
    current_tab,
    set_cur_window,
    tab_list_wins,
    win_get_buf,
    win_get_option,
    win_set_option,
)


def preview_windows_in_tab(
    nvim: Nvim, tab: Optional[Tabpage] = None
) -> Iterator[Window]:
    tab = tab or current_tab(nvim)
    wins = tab_list_wins(nvim, tab=tab)
    for win in wins:
        opt: bool = win_get_option(nvim, win=win, key="previewwindow")
        if opt:
            yield win


def _open_preview(nvim: Nvim) -> Window:
    win = next(preview_windows_in_tab(nvim), None)
    if win:
        set_cur_window(nvim, win=win)
        return win
    else:
        nvim.api.command("new")
        win = cur_window(nvim)
        buf = win_get_buf(nvim, win=win)
        win_set_option(nvim, win=win, key="previewwindow", val=True)
        buf_set_option(nvim, buf=buf, key="bufhidden", val="wipe")
        height = nvim.options["previewheight"]
        nvim.api.win_set_height(win, height)
        return win


def set_preview(nvim: Nvim, preview: str) -> Buffer:
    win = _open_preview(nvim)
    buf = win_get_buf(nvim, win=win)
    buf_set_option(nvim, buf=buf, key="buftype", val="nofile")
    buf_set_option(nvim, buf=buf, key="modifiable", val=True)
    buf_set_lines(nvim, buf=buf, lo=0, hi=-1, lines=preview.splitlines())
    buf_set_option(nvim, buf=buf, key="modifiable", val=False)
    return buf
